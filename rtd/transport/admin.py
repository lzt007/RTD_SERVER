"""Local operations API; JSON transport is separate from the game's gzip DTOs."""
import json
import urllib.parse
from ..common import compact
from ..operations.configuration import ConfigurationError

MAX_BODY=1024*1024


def handle_admin(handler,api):
    status=200
    try:
        if handler.headers.get('Transfer-Encoding'):
            raise ConfigurationError('Chunked request bodies are unsupported',400)
        try:size=int(handler.headers.get('Content-Length','0'))
        except ValueError:raise ConfigurationError('Invalid Content-Length',400) from None
        if size<0:raise ConfigurationError('Invalid Content-Length',400)
        # Consume bounded request bodies even on routing/method errors. Closing
        # with unread input can reset Windows TCP before the JSON error arrives.
        payload=handler.rfile.read(min(size,MAX_BODY+1)) if size else b''
        if size>MAX_BODY:raise ConfigurationError('Request body exceeds 1 MiB',413)
        if len(payload)!=size:raise ConfigurationError('Incomplete request body',400)
        path=urllib.parse.urlsplit(handler.path).path
        parts=path.removeprefix('/admin/v1/').split('/')
        resource=parts[0];key=parts[1] if len(parts)==2 else None
        if (len(parts)>2 or resource not in ('config','gachas','events','catalog','players','presents')
                or (key is not None and (not key or resource in ('config','catalog','players')))
                or (resource=='presents' and key is None)):
            raise ConfigurationError('Management resource not found',404)
        method=handler.command
        if method=='GET':
            if resource=='players':result=dict(data=api.delivery.players())
            elif resource=='presents':result=dict(data=api.delivery.read(key))
            elif resource=='catalog':result=dict(data=api.operations.catalog())
            else:
                cfg=api.operations.read();availability=api.operations.availability(cfg)
                if resource=='config':result=dict(data=cfg,availability=availability)
                else:
                    data=cfg[resource];active=availability[resource]
                    if key is not None:
                        data=next((row for row in data if str(row['id'])==key),None)
                        if data is None:raise ConfigurationError('Resource not found',404)
                        active=next(row for row in active if str(row['id'])==key)
                    result=dict(data=data,revision=cfg['revision'],availability=active)
        else:
            if not ((resource=='config' and key is None and method=='PUT') or
                    (resource=='presents' and key is not None and method=='POST') or
                    (resource in ('gachas','events') and key is not None and
                     (method in ('PUT','PATCH') or (method=='DELETE' and resource=='events')))):
                raise ConfigurationError('Unsupported method',405)
            body=None
            if method!='DELETE':
                if handler.headers.get_content_type()!='application/json':
                    raise ConfigurationError('Content-Type must be application/json',415)
                if size<=0:raise ConfigurationError('Expected a JSON body',400)
                try:
                    body=json.loads(payload.decode('utf-8'))
                except (ValueError,UnicodeError):raise ConfigurationError('Malformed UTF-8 JSON body',400) from None
            if resource=='presents':
                result=api.delivery.send(key,body)
                status=200 if result['replayed'] else 201
            else:
                cfg=api.operations.update(resource,key,body,method)
                result=dict(data=cfg,availability=api.operations.availability(cfg))
    except ConfigurationError as exc:
        status=exc.status
        codes={400:'malformed_request',404:'not_found',405:'method_not_allowed',409:'revision_conflict',
               413:'body_too_large',415:'unsupported_media_type',422:'invalid_configuration'}
        result=dict(error=dict(code=codes.get(status,'configuration_error'),message=str(exc)))
    except Exception:
        import traceback
        traceback.print_exc()
        status=500;result=dict(error=dict(code='internal_error',message='Internal configuration error'))
    body=compact(result).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type','application/json; charset=utf-8')
    handler.send_header('Content-Length',str(len(body)))
    handler.send_header('Connection','close')
    handler.end_headers();handler.wfile.write(body);handler.close_connection=True
