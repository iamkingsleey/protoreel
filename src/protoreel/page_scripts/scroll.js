/* ([x, y, dx, dy]) => scrolls whatever is under the point, the way a mouse wheel would:
   the nearest scrollable box, or else the page, going into same-origin iframes.
   Scrolling is instant so it stays on Protoreel's frame-by-frame clock. */
([x, y, dx, dy]) => {
  let doc = document;
  for (;;) {
    const view = doc.defaultView;
    const el = doc.elementFromPoint(x, y);
    if (el && el.tagName === 'IFRAME') {
      let inner = null;
      try { inner = el.contentDocument; } catch (e) {}
      if (inner) {
        const r = el.getBoundingClientRect();
        const k = el.offsetWidth ? r.width / el.offsetWidth : 1;
        x = (x - r.left) / k - el.clientLeft;
        y = (y - r.top) / k - el.clientTop;
        doc = inner;
        continue;
      }
    }
    for (let n = el; n && n !== doc.body && n !== doc.documentElement; n = n.parentElement) {
      const style = view.getComputedStyle(n);
      const canY = dy && /(auto|scroll|overlay)/.test(style.overflowY) && n.scrollHeight > n.clientHeight;
      const canX = dx && /(auto|scroll|overlay)/.test(style.overflowX) && n.scrollWidth > n.clientWidth;
      if (canY || canX) { n.scrollBy({ left: dx, top: dy, behavior: 'instant' }); return; }
    }
    view.scrollBy({ left: dx, top: dy, behavior: 'instant' });
    return;
  }
}
