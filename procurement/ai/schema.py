# filepath: procurement/ai/schema.py
from datetime import date
from django.core.exceptions import ValidationError
from common.numbers import parse_money,parse_quantity,format_money,format_quantity
from .config import AIError


def nullable_text(length: int) -> dict:
    return {'type':['string','null'],'maxLength':length}


FIELDS = {'kind':{'type':['string','null'],'enum':['GOODS','SERVICES',None]},
          'title':nullable_text(200),'reason':nullable_text(1500),
          'destination':nullable_text(500),'needed_on':nullable_text(10)}
ITEM_FIELDS = {'name':nullable_text(200),'unit':nullable_text(40),
               'quantity':nullable_text(24),'unit_price':nullable_text(24)}
SCHEMA = {'type':'object','properties':FIELDS|{'items':{'type':'array','maxItems':10,
          'items':{'type':'object','properties':ITEM_FIELDS,'required':list(ITEM_FIELDS),'additionalProperties':False}}},
          'required':[*FIELDS,'items'],'additionalProperties':False}


def _text(value: object, limit: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value,str) or len(value)>limit or any(ord(c)<32 and c not in '\n\r\t' for c in value):
        raise AIError('Hasil AI tidak sesuai format. Lengkapi form secara manual.')
    return value.strip() or None


def clean_suggestion(data: object) -> dict:
    if not isinstance(data,dict) or set(data) != set(SCHEMA['required']):
        raise AIError('Hasil AI tidak sesuai format. Lengkapi form secara manual.')
    if data['kind'] not in ('GOODS','SERVICES',None):
        raise AIError('Jenis pengadaan dari AI tidak valid. Pilih secara manual.')
    result = {key:_text(data[key],spec.get('maxLength',20)) for key,spec in FIELDS.items()}
    if result['needed_on']:
        try:
            if date.fromisoformat(result['needed_on']).isoformat()!=result['needed_on']:
                raise ValueError
        except ValueError:
            raise AIError('Tanggal dari AI tidak valid. Isi tanggal secara manual.') from None
    if not isinstance(data['items'],list) or len(data['items'])>10:
        raise AIError('Hasil AI melebihi batas sepuluh item. Ringkas masukan Anda.')
    items=[]
    try:
        for row in data['items']:
            if not isinstance(row,dict) or set(row)!=set(ITEM_FIELDS):
                raise AIError('Rincian dari AI tidak sesuai format. Gunakan input manual.')
            item={key:_text(row[key],spec['maxLength']) for key,spec in ITEM_FIELDS.items()}
            if item['quantity'] is not None:
                item['quantity']=format_quantity(parse_quantity(item['quantity'])).rstrip('0').rstrip('.')
            if item['unit_price'] is not None:
                item['unit_price']=format_money(parse_money(item['unit_price']))
            items.append(item)
    except ValidationError:
        raise AIError('Angka dari AI tidak valid atau melebihi batas. Lengkapi form secara manual.') from None
    result['items']=items
    warnings=[]
    labels={'kind':'Jenis pengadaan','reason':'Alasan kebutuhan','destination':'Tujuan layanan','needed_on':'Tanggal kebutuhan'}
    warnings.extend(label+' belum tersedia.' for key,label in labels.items() if result[key] is None)
    for index,item in enumerate(items,1):
        missing=[{'name':'nama','unit':'satuan','quantity':'jumlah','unit_price':'harga'}[key] for key,value in item.items() if value is None]
        if missing:warnings.append(f'Item {index}: lengkapi '+', '.join(missing)+'.')
    if not items:warnings.append('Rincian item belum tersedia. Tambahkan secara manual.')
    result['warnings']=warnings
    return result
