import katex from 'katex';
import 'katex/dist/katex.min.css';

export function renderMath(text, element, displayMode) {
  katex.render(text, element, { displayMode, trust: false, throwOnError: false, maxExpand: 200, maxSize: 12 });
}
