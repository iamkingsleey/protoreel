/* Draws a macOS-style pointer on top of the page. Called with the cursor scale;
   afterwards window.__cursor(x, y, pressed, visible) moves it. */
(scale) => {
  const c = document.createElement('div');
  c.innerHTML = '<svg width="24" height="30" viewBox="0 0 24 30" style="display:block;overflow:visible">' +
    '<path d="M2 2 L2 23.5 L7.6 18.4 L11.3 26.6 L15.1 25 L11.5 16.9 L19 16.9 Z" fill="#000" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  Object.assign(c.style, {position:'fixed', left:'0', top:'0', zIndex:'2147483647', pointerEvents:'none',
    transformOrigin:'2px 2px', filter:'drop-shadow(0 2px 3px rgba(0,0,0,.28))'});
  document.documentElement.appendChild(c);
  window.__cursor = (x, y, down, show) => {
    c.style.display = show ? 'block' : 'none';
    c.style.transform = `translate(${x - 2}px, ${y - 2}px) scale(${scale * (down ? 0.9 : 1)})`;
  };
}
