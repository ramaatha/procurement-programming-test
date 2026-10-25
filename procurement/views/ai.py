# filepath: procurement/views/ai.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.debug import sensitive_post_parameters,sensitive_variables
from django.views.decorators.http import require_POST
from accounts.models import Role
from procurement.policies import active_actor
from procurement.ai import client
from procurement.ai.config import configuration,AIError
from procurement.ai.images import prepare_image
from procurement.ai.quota import reserve,release
from procurement.ai.schema import clean_suggestion


@sensitive_post_parameters('text','csrfmiddlewaretoken')
@sensitive_variables()
@login_required
@require_POST
def assist_draft(request):
    if active_actor(request.user.pk).role!=Role.REQUESTER:
        return JsonResponse({'error':'Bantuan AI hanya tersedia untuk Pemohon.'},status=403)
    try:
        config=configuration()
        if config is None:
            raise AIError('Bantuan AI belum diaktifkan. Anda tetap dapat mengisi form secara manual.',503)
        mode=request.POST.get('mode')
        text=request.POST.get('text','')
        files=request.FILES.getlist('image')
        if mode=='text' and not files and isinstance(text,str) and 1<=len(text.strip())<=1500 and len(text)<=1500:
            image_url=None
        elif mode=='image' and not text.strip() and len(files)==1:
            image_url=prepare_image(files[0])
        else:
            raise AIError('Isi kebutuhan maksimal 1.500 karakter atau pilih satu gambar JPG/PNG maksimal 2 MB.',400)
        token=reserve(request.user.pk)
        try:
            result=clean_suggestion(client.request_completion(api_key=config.api_key,text=text.strip(),image_url=image_url))
        finally:
            release(token)
        response=JsonResponse({'suggestion':result})
    except AIError as error:
        response=JsonResponse({'error':str(error)},status=error.status)
        if error.status==429:response['Retry-After']='60'
    response['Cache-Control']='no-store'
    return response
