/* Virtual clock. Injected before the page loads, so rAF, timers, performance.now, Date.now and
   CSS/Web animations all run on time that Protoreel advances by exactly one frame at a time.
   window.__advance(ms) moves the clock forward. */
(() => {
  let now = 0; const epoch = Date.now();
  const raf = new Map(); let rid = 0;
  const timers = new Map(); let tid = 0;
  performance.now = () => now;
  Date.now = () => epoch + now;
  window.requestAnimationFrame = cb => { const id = ++rid; raf.set(id, cb); return id; };
  window.cancelAnimationFrame = id => { raf.delete(id); };
  window.setTimeout = (fn, ms = 0, ...a) => { const id = ++tid; timers.set(id, {at: now + Math.max(0, +ms || 0), fn, a}); return id; };
  window.setInterval = (fn, ms = 0, ...a) => { const id = ++tid; const e = Math.max(1, +ms || 0); timers.set(id, {at: now + e, fn, a, every: e}); return id; };
  window.clearTimeout = window.clearInterval = id => { timers.delete(id); };
  const seen = new WeakMap(), fin = new WeakSet();
  window.__advance = (ms) => {
    const end = now + ms;
    for (;;) {
      let pick = null;
      for (const [id, t] of timers) if (t.at <= end && (!pick || t.at < pick[1].at)) pick = [id, t];
      if (!pick) break;
      const [id, t] = pick; now = t.at;
      if (t.every) t.at += t.every; else timers.delete(id);
      try { typeof t.fn === 'function' ? t.fn(...t.a) : (0, eval)(t.fn); } catch (e) { console.error(e); }
    }
    now = end;
    for (const an of document.getAnimations()) {
      try {
        if (fin.has(an)) continue;
        if (!seen.has(an)) { an.pause(); seen.set(an, an.currentTime || 0); }
        const t = seen.get(an) + ms; seen.set(an, t); an.currentTime = t;
        // a frozen animation never fires 'finish' on its own — finish it once its time is up, so pages waiting on it carry on
        const end = an.effect && an.effect.getComputedTiming ? an.effect.getComputedTiming().endTime : Infinity;
        if (isFinite(end) && t >= end) { fin.add(an); an.finish(); }
      } catch (e) {}
    }
    const cbs = [...raf.values()]; raf.clear();
    for (const cb of cbs) { try { cb(now); } catch (e) { console.error(e); } }
  };
})();
