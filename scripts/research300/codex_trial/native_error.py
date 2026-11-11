"""Actionable native errors derived solely from this candidate's own job."""
import json

def native_error(native, diagnostic, receipt):
    message=diagnostic.get('error',receipt.get('error','Native process failed'))
    detail=diagnostic.get('detail')
    fields=['returncode','phase','command','error','capability','reason','inputFields']
    result={'nativeExecutionFailed':True,'errorCode':diagnostic.get('errorCode'),
            'message':str(message).split('\n\nArtifact feedback:',1)[0],
            'detail':{k:detail[k] for k in fields if k in detail} if isinstance(detail,dict) else detail}
    audits=[p for p in native.rglob('native-physics-audit.json') if p.is_file() and not p.is_symlink()
            and p.resolve().is_relative_to(native.resolve())]
    if len(audits)==1:
        audit=json.loads(audits[0].read_text(encoding='utf8'))
        result['nativePhysicsDiagnostic']={'passed':audit.get('passed'),'failures':audit.get('failures'),
            'loads':audit.get('loads'),'settingsFailures':audit.get('settings',{}).get('failures')}
    return result
