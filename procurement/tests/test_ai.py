# filepath: procurement/tests/test_ai.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings
from PIL import Image
import httpx

from accounts.models import Role
from procurement.models import PurchaseRequest, AuditEvent
from procurement.tests.factories import user


def suggestion():
    return dict(kind='SERVICES',title='Pemeriksaan jaringan',reason=None,destination='Kantor Demo',
                needed_on=None,items=[dict(name='Pemeriksaan jaringan',unit='paket',quantity='1',unit_price='250000.00')])


def image_file():
    buffer=io.BytesIO()
    Image.new('RGB',(80,60),'white').save(buffer,format='PNG')
    return SimpleUploadedFile('contoh.png',buffer.getvalue(),content_type='image/png')


class AIEndpointTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.area=Path(self.temp.name)
        self.config=self.area/'ai.json'
        self.env=patch.dict(os.environ,{'PROCUREMENT_AI_CONFIG':str(self.config),'GROQ_API_KEY':''})
        self.env.start();self.addCleanup(self.env.stop)
        self.options=override_settings(DATA_DIR=self.area)
        self.options.enable();self.addCleanup(self.options.disable)
        self.owner=user(Role.REQUESTER)
        self.client.force_login(self.owner)

    def enable_ai(self):
        self.config.write_text(json.dumps({'api_key':'synthetic-unit-test-key'}),encoding='utf-8')

    def test_anonymous_assistance_requires_login(self):
        response=Client().post('/requests/assist/',{'mode':'text','text':'Butuh satu monitor'})
        self.assertEqual(response.status_code,302)

    def test_manual_form_stays_available_when_ai_is_not_configured(self):
        page=self.client.get('/requests/new/')
        self.assertContains(page,'Bantu Isi dengan AI')
        self.assertContains(page,'Simpan Draf')
        response=self.client.post('/requests/assist/',{'mode':'text','text':'Butuh satu monitor'})
        self.assertEqual(response.status_code,503)

    def test_assistance_requires_csrf_and_current_requester_role(self):
        self.enable_ai()
        client=Client(enforce_csrf_checks=True);client.force_login(self.owner)
        self.assertEqual(client.post('/requests/assist/',{'mode':'text','text':'Butuh monitor'}).status_code,403)
        self.owner.role=Role.ADMIN;self.owner.save(update_fields=['role'])
        self.assertEqual(self.client.post('/requests/assist/',{'mode':'text','text':'Butuh monitor'}).status_code,403)

    def test_suggestions_do_not_save_business_data(self):
        self.enable_ai()
        with patch('procurement.ai.client.request_completion',return_value=suggestion()) as upstream:
            response=self.client.post('/requests/assist/',{'mode':'text','text':'Pemeriksaan satu paket 250000'})
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(response.json()['suggestion']['items'][0]['unit_price'],'250000.00')
        self.assertFalse(PurchaseRequest.objects.exists());self.assertFalse(AuditEvent.objects.exists())
        upstream.assert_called_once()

    def test_bad_and_mixed_input_never_calls_provider(self):
        self.enable_ai()
        cases=[{'mode':'text','text':'x'*1501},{'mode':'text','text':''},
               {'mode':'image','image':SimpleUploadedFile('fake.png',b'not image',content_type='image/png')},
               {'mode':'image','image':image_file(),'text':'unexpected'},
               {'mode':'text','text':'Butuh monitor','image':image_file()}]
        with patch('procurement.ai.client.request_completion') as upstream:
            for payload in cases:
                with self.subTest(mode=payload['mode']):
                    self.assertEqual(self.client.post('/requests/assist/',payload).status_code,400)
        upstream.assert_not_called()

    def test_image_is_reencoded_and_not_stored_as_attachment(self):
        self.enable_ai()
        with patch('procurement.ai.client.request_completion',return_value=suggestion()) as upstream:
            response=self.client.post('/requests/assist/',{'mode':'image','image':image_file()})
        self.assertEqual(response.status_code,200,response.content)
        data=upstream.call_args.kwargs['image_url']
        self.assertTrue(data.startswith('data:image/jpeg;base64,'))
        self.assertFalse(any(self.area.glob('*.png')))

    def test_upstream_failure_is_safe_and_never_creates_request(self):
        from procurement.ai.config import AIError
        self.enable_ai()
        with patch('procurement.ai.client.request_completion',side_effect=AIError('Layanan AI sedang sibuk.',503)):
            response=self.client.post('/requests/assist/',{'mode':'text','text':'Butuh satu monitor'})
        self.assertEqual(response.status_code,503)
        self.assertNotIn('synthetic-unit-test-key',response.content.decode())
        self.assertFalse(PurchaseRequest.objects.exists())


class AISchemaTests(SimpleTestCase):
    def test_canonical_numbers_and_missing_values_remain_explicit(self):
        from procurement.ai.schema import clean_suggestion
        result=clean_suggestion(suggestion())
        self.assertIsNone(result['reason'])
        self.assertEqual(result['items'][0]['unit_price'],'250000.00')
        self.assertTrue(result['warnings'])

    def test_untrusted_structure_or_numbers_are_not_accepted(self):
        from procurement.ai.config import AIError
        from procurement.ai.schema import clean_suggestion
        for changes in ({'status':'APPROVED'},{'items':[{'name':'A','unit':'unit','quantity':'1','unit_price':250000}]},
                        {'items':[{'name':'A','unit':'unit','quantity':'1','unit_price':'1,250.50'}]},
                        {'items':[{'name':'A','unit':'unit','quantity':'1','unit_price':'92233720368547758.08'}]},
                        {'items':suggestion()['items']*11}):
            with self.subTest(changes=changes),self.assertRaises(AIError):
                clean_suggestion(suggestion()|changes)

    def test_null_item_values_are_not_invented(self):
        from procurement.ai.schema import clean_suggestion
        data=suggestion();data['items'][0].update(quantity=None,unit_price=None)
        result=clean_suggestion(data)
        self.assertIsNone(result['items'][0]['quantity']);self.assertIsNone(result['items'][0]['unit_price'])


class AIQuotaTests(SimpleTestCase):
    def test_quota_limits_parallel_requests_and_survives_new_connection(self):
        from procurement.ai.quota import reserve,release
        from procurement.ai.config import AIError
        with tempfile.TemporaryDirectory() as area,override_settings(DATA_DIR=Path(area)):
            token=reserve(1)
            with self.assertRaises(AIError):reserve(2)
            release(token)
            for _ in range(4):release(reserve(1))
            with self.assertRaises(AIError):reserve(1)
            for _ in range(5):release(reserve(2))
            with self.assertRaises(AIError):reserve(3)

    def test_only_one_reservation_wins_concurrent_attempts(self):
        from procurement.ai.quota import reserve,release
        from procurement.ai.config import AIError
        with tempfile.TemporaryDirectory() as area,override_settings(DATA_DIR=Path(area)):
            def attempt(actor):
                try:return reserve(actor)
                except AIError:return None
            with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,[1,2]))
            winners=[value for value in results if value]
            self.assertEqual(len(winners),1)
            release(winners[0])


class AIClientTests(SimpleTestCase):
    @contextmanager
    def transport(self,handler):
        original=httpx.AsyncClient
        with patch('procurement.ai.client.httpx.AsyncClient',side_effect=lambda **options:
                   original(transport=httpx.MockTransport(handler),timeout=options['timeout'],
                            follow_redirects=options['follow_redirects'],trust_env=False)):
            yield

    def test_client_conserves_tokens_and_calls_fixed_endpoint_once(self):
        from procurement.ai.client import request_completion
        requests=[]
        def handler(request):
            requests.append(request)
            return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(suggestion())}}]})
        with self.transport(handler):
            self.assertEqual(request_completion(api_key='synthetic-key',text='Butuh jasa',image_url=None),suggestion())
        self.assertEqual(len(requests),1)
        request=requests[0]
        payload=json.loads(request.content)
        self.assertEqual(str(request.url),'https://api.groq.com/openai/v1/chat/completions')
        self.assertEqual(payload['reasoning_effort'],'none')
        self.assertEqual(payload['max_completion_tokens'],1200)
        self.assertEqual(payload['model'],'qwen/qwen3.8-27b')
        self.assertEqual(len(payload['messages']),2)

    def test_timeout_and_rate_limit_are_safe_without_retry(self):
        from procurement.ai.client import request_completion
        from procurement.ai.config import AIError
        for status in (429,401,500,302):
            calls=[]
            def handler(request):
                calls.append(request)
                return httpx.Response(status,headers={'location':'https://other.invalid'})
            with self.transport(handler):
                with self.assertRaises(AIError):request_completion(api_key='synthetic-key',text='Butuh jasa',image_url=None)
                self.assertEqual(len(calls),1)

    def test_total_deadline_cancels_slow_stream_and_quota_can_be_released(self):
        from procurement.ai.client import request_completion
        from procurement.ai.config import AIError
        from procurement.ai.quota import reserve,release
        closed=[]
        class SlowStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                for _ in range(100):
                    await asyncio.sleep(.02)
                    yield b'x'
            async def aclose(self):closed.append(True)
        async def handler(request):return httpx.Response(200,stream=SlowStream())
        with tempfile.TemporaryDirectory() as area,override_settings(DATA_DIR=Path(area)),self.transport(handler),patch('procurement.ai.client.TOTAL_TIMEOUT',.08):
            token=reserve(1)
            started=time.monotonic()
            try:
                with self.assertRaises(AIError):request_completion(api_key='synthetic-key',text='Butuh jasa',image_url=None)
            finally:release(token)
            self.assertLess(time.monotonic()-started,.6)
            self.assertEqual(closed,[True])
            release(reserve(2))

    def test_truncated_transport_returns_safe_error(self):
        from procurement.ai.client import request_completion
        from procurement.ai.config import AIError
        def handler(request):raise httpx.RemoteProtocolError('synthetic truncated chunks')
        with self.transport(handler),self.assertRaises(AIError):
            request_completion(api_key='synthetic-key',text='Butuh jasa',image_url=None)


class AIConfigurationTests(SimpleTestCase):
    def test_private_key_file_never_overwrites_existing_configuration(self):
        from deploy.ai import create_configuration
        with tempfile.TemporaryDirectory() as area:
            path=Path(area)/'private/ai.json'
            create_configuration(path,'synthetic-first-api-key')
            before=path.read_bytes()
            with self.assertRaises(FileExistsError):create_configuration(path,'synthetic-second-api-key')
            self.assertEqual(path.read_bytes(),before)

    def test_bad_configuration_disables_optional_feature(self):
        from procurement.ai.config import configuration
        with tempfile.TemporaryDirectory() as area:
            path=Path(area)/'ai.json'
            with patch.dict(os.environ,{'GROQ_API_KEY':'','PROCUREMENT_AI_CONFIG':str(path)}):
                self.assertIsNone(configuration())
                path.write_text('{bad json',encoding='utf-8')
                self.assertIsNone(configuration())
                path.write_text(json.dumps({'api_key':'synthetic-valid-key','endpoint':'https://evil.invalid'}),encoding='utf-8')
                self.assertIsNone(configuration())
