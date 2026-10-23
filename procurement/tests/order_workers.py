# filepath: procurement/tests/order_workers.py
"""Run SQLite race workers inside a process that the parent can terminate."""
import multiprocessing
import os


def _run(database, jobs, output):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    import time
    import traceback

    try:
        if not all(job['action']=='pause' for job in jobs):
            os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
            from django.conf import settings
            settings.DATABASES['default'] = database
            import django
            django.setup()
        gate = Barrier(len(jobs))

        def execute(job):
            if job['action']=='pause':
                gate.wait(timeout=5)
                time.sleep(job['seconds'])
                return 'ok'
            from uuid import UUID
            from django.core.exceptions import ValidationError
            from django.db import close_old_connections
            from common.actions import ActionContext
            from common.errors import ConflictError
            from procurement.services import orders, requests, sourcing
            close_old_connections()
            try:
                ctx = ActionContext(job['actor_id'],UUID(job['nonce']),job['version'])
                gate.wait(timeout=5)
                if job['action']=='issue':
                    orders.issue_order(ctx,request_id=UUID(job['request_id']))
                elif job['action']=='cancel':
                    requests.cancel_request(ctx,request_id=UUID(job['request_id']),reason='Batal')
                elif job['action']=='deactivate':
                    sourcing.save_vendor(ctx,vendor_id=UUID(job['vendor_id']),name='Nama baru',contact='Kontak baru',is_active=False)
                elif job['action']=='receipt':
                    from procurement.models import PurchaseOrder
                    from procurement.services.receipts import post_receipt
                    from procurement.tests.receipt_fixtures import receipt_data
                    order = PurchaseOrder.objects.get(pk=UUID(job['order_id']))
                    post_receipt(ctx,order_id=order.pk,data=receipt_data(order,'6','0',''))
                elif job['action']=='close':
                    orders.close_order(ctx,order_id=UUID(job['order_id']),reason='Tidak dilanjutkan')
                else:
                    raise ValueError('Unknown test action')
                return 'ok'
            except ConflictError:
                return 'conflict'
            except ValidationError:
                return 'invalid'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            results = list(pool.map(execute,jobs))
        output.send(dict(results=results))
    except BaseException:
        output.send(dict(error=traceback.format_exc(limit=6)[-3000:]))
    finally:
        output.close()


def run_race(database, jobs, *, timeout=15):
    expected = database.get('TEST',{}).get('NAME')
    if not expected or str(database['NAME'])!=str(expected) or str(expected)==':memory:':
        raise ValueError('Race workers require the separate file-backed test database.')
    spawn = multiprocessing.get_context('spawn')
    receiver,sender = spawn.Pipe(duplex=False)
    process = spawn.Process(target=_run,args=(database,jobs,sender),daemon=True)
    process.start()
    sender.close()
    try:
        process.join(timeout)
        if process.is_alive():
            process.terminate()
            process.join(1)
            if process.is_alive():
                process.kill()
                process.join(1)
            raise TimeoutError('Concurrency test exceeded its process deadline.')
        if not receiver.poll(1):
            raise AssertionError(f'Race worker exited without results: {process.exitcode}')
        result = receiver.recv()
        if 'error' in result:
            raise AssertionError(result['error'])
        if process.exitcode!=0:
            raise AssertionError(f'Race worker failed: {process.exitcode}')
        return result['results']
    finally:
        if process.is_alive():
            process.kill()
            process.join(1)
        receiver.close()
        if not process.is_alive():
            process.close()
