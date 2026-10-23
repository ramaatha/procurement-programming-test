# filepath: config/views.py
from django.shortcuts import render
from django.http import HttpResponse


def error_page(request, status):
    content = {
        400: ('Permintaan Tidak Valid','Periksa alamat atau isian, lalu coba kembali.'),
        403: ('Akses Tidak Diizinkan','Akun Anda tidak dapat menjalankan tindakan ini.'),
        404: ('Halaman Tidak Ditemukan','Alamat tidak tersedia atau Anda tidak mempunyai akses ke dokumen ini.'),
        500: ('Permintaan Belum Dapat Diselesaikan','Terjadi gangguan. Periksa detail dokumen sebelum mengulangi tindakan.'),
    }
    title,message = content[status]
    return render(request,'errors/error.html',dict(error_title=title,error_message=message,error_code=status),status=status)


def bad_request(request, exception): return error_page(request,400)
def permission_denied(request, exception): return error_page(request,403)
def page_not_found(request, exception): return error_page(request,404)
def server_error(request): return error_page(request,500)
def favicon(request): return HttpResponse(status=204)


def csrf_failure(request, reason=''):
    return render(request,'errors/error.html',dict(error_title='Sesi Form Perlu Diperbarui',
                  error_message='Muat ulang halaman asal untuk memperoleh form baru. Periksa hasil sebelumnya sebelum mengirim kembali.',error_code=403),status=403)
