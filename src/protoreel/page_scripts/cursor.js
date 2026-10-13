/* Draws the on-screen pointer on top of the page. Called with [scale, style]:
     "arrow" — a macOS-style pointer, for desktop prototypes
     "touch" — a soft fingertip dot that presses in, for mobile prototypes
   Afterwards window.__cursor(x, y, pressed, visible) moves it. */
([scale, style]) => {
  const c = document.createElement('div');
  Object.assign(c.style, {position:'fixed', left:'0', top:'0', zIndex:'2147483647', pointerEvents:'none'});
  document.documentElement.appendChild(c);

  if (style === 'touch') {
    const size = 34 * scale;  // roughly a fingertip on a phone screen
    Object.assign(c.style, {width: size + 'px', height: size + 'px', borderRadius: '50%',
      background: 'rgba(30, 34, 40, .22)', border: '2px solid rgba(255, 255, 255, .9)',
      boxShadow: '0 1px 2px rgba(0,0,0,.18), 0 6px 16px rgba(0,0,0,.16)', boxSizing: 'border-box'});
    window.__cursor = (x, y, down, show) => {
      c.style.display = show ? 'block' : 'none';
      c.style.background = down ? 'rgba(30, 34, 40, .36)' : 'rgba(30, 34, 40, .22)';
      c.style.transform = `translate(${x - size / 2}px, ${y - size / 2}px) scale(${down ? 0.82 : 1})`;
    };
    return;
  }

  c.innerHTML = '<svg width="24" height="30" viewBox="0 0 24 30" style="display:block;overflow:visible">' +
    '<path d="M2 2 L2 23.5 L7.6 18.4 L11.3 26.6 L15.1 25 L11.5 16.9 L19 16.9 Z" fill="#000" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  Object.assign(c.style, {transformOrigin:'2px 2px', filter:'drop-shadow(0 2px 3px rgba(0,0,0,.28))'});
  window.__cursor = (x, y, down, show) => {
    c.style.display = show ? 'block' : 'none';
    c.style.transform = `translate(${x - 2}px, ${y - 2}px) scale(${scale * (down ? 0.9 : 1)})`;
  };
}
