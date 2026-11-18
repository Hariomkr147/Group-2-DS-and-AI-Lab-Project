import { useEffect, useRef } from 'react';

function Formula({ text, display }) {
  const element = useRef(null);
  useEffect(() => {
    let active = true;
    import('./math.js').then(({ renderMath }) => {
      if (active) renderMath(text, element.current, display);
    }).catch(() => {});
    return () => { active = false; };
  }, [text, display]);
  return <span className={display ? 'math-block' : undefined} ref={element}>{text}</span>;
}

export function RichText({ text }) {
  const tokens = text.split(/(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\(.+?\\\)|(?<![\w$])\$(?![\d\s$])[^\n$]+?\$(?!\$))/);
  return tokens.map((part, index) => {
    if (index % 2 === 0) return part;
    const size = part.startsWith('$$') || part.startsWith('\\') ? 2 : 1;
    return <Formula key={index} text={part.slice(size, -size)} display={part.startsWith('$$') || part.startsWith('\\[')} />;
  });
}

export function SourceLink({ resource }) {
  let href;
  try {
    const url = new URL(resource.url);
    if (['https:', 'http:'].includes(url.protocol)) href = url.href;
  } catch { /* source may have no URL */ }
  const title = sourceTitle(resource);
  return href ? <a href={href} target="_blank" rel="noopener noreferrer">{title}</a> : <span>{title}</span>;
}

export function sourceTitle(resource) {
  const page = resource.page === 'to fill' ? '' : resource.page;
  return page ? `${resource.source} · Page ${page}` : resource.source;
}
