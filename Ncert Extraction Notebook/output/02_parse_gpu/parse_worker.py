if __name__ == '__main__':
    import json, os, sys, traceback
    from pathlib import Path

    gpu, jobs_file, source_root, output_root, home = sys.argv[1:]
    os.environ['CUDA_VISIBLE_DEVICES'] = gpu
    os.environ['MINERU_HOME'] = home
    os.environ['MINERU_MODEL_SMALL_BACKEND'] = 'torch'
    os.environ['MINERU_MODEL_SOURCE'] = 'local'
    os.environ['MINERU_DEVICE_MODE'] = 'cuda'
    os.environ['MINERU_MODEL_ONNX_DEVICE'] = 'cpu'
    import torch
    assert torch.cuda.is_available(), 'CUDA required'
    from mineru.model.runtime.device import resolve_torch_device
    assert resolve_torch_device().device.startswith('cuda'), 'MinerU CUDA required'
    from mineru import MinerUParser
    from mineru.parser.writer import FileBasedDataWriter

    parser = MinerUParser(tier='basic', parse_mode='auto')
    jobs = json.loads(Path(jobs_file).read_text())
    with (Path(output_root) / ('worker-' + gpu + '.jsonl')).open('a') as log:
        for job in jobs:
            pdf = Path(source_root) / job['file']
            chapter = Path(output_root) / Path(job['file']).stem
            chapter.mkdir(exist_ok=True)
            for page in range(1, job['pages'] + 1):
                done = chapter / f'{page:04d}.done'
                if done.exists():
                    continue
                try:
                    result = parser.parse(str(pdf), page_range=str(page))
                    assert [p.page_idx + 1 for p in result.pages] == [page]
                    page_dir = chapter / f'{page:04d}'
                    page_dir.mkdir(exist_ok=True)
                    result.save(FileBasedDataWriter(str(page_dir)))
                    markdown = page_dir / 'markdown.md'
                    assert markdown.exists()
                    status = 'empty' if not markdown.read_text(encoding='utf-8').strip() else 'parsed'
                    done.write_text(status)
                    log.write(json.dumps({'file': job['file'], 'page': page, 'status': status}) + '\n')
                except Exception as exc:
                    log.write(json.dumps({'file': job['file'], 'page': page, 'status': 'error', 'error': str(exc), 'trace': traceback.format_exc()[-1200:]}) + '\n')
                log.flush()
