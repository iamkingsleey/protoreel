/* (selector) => [left, top, width, height] of the first match, in the viewport of the top page,
   or null. Looks inside same-origin iframes too, allowing for frames that are scaled
   (an app running inside a phone frame, for example). */
(selector) => {
  function find(doc, offsetX, offsetY, scale) {
    const el = doc.querySelector(selector);
    if (el) {
      const r = el.getBoundingClientRect();
      return [offsetX + r.left * scale, offsetY + r.top * scale, r.width * scale, r.height * scale];
    }
    for (const frame of doc.querySelectorAll('iframe')) {
      let inner = null;
      try { inner = frame.contentDocument; } catch (e) {}  // cross-origin: not ours to look into
      if (!inner) continue;
      const r = frame.getBoundingClientRect();
      const k = frame.offsetWidth ? r.width / frame.offsetWidth : 1;  // CSS transforms on the frame
      const hit = find(inner, offsetX + (r.left + frame.clientLeft * k) * scale,
                       offsetY + (r.top + frame.clientTop * k) * scale, scale * k);
      if (hit) return hit;
    }
    return null;
  }
  return find(document, 0, 0, 1);
}
