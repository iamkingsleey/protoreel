/* recBackground(document, color): paints a solid colour under the page content.
   The layer fades away when the page switches to a dark colour scheme. */
function recBackground(doc, color){
  var w = doc.defaultView;
  if(w.__recBgObs){ try{ w.__recBgObs.disconnect(); }catch(e){} w.__recBgObs = null; }
  var old = doc.getElementById('__rec_bgl'); if(old) old.remove();
  if(!color) return;
  /* a layer under the page content: covers the page background in light mode, fades away in dark mode */
  var layer = doc.createElement('div'); layer.id = '__rec_bgl';
  layer.setAttribute('style', 'position:fixed;inset:0;z-index:-1;pointer-events:none;background:' + color + ';opacity:1;transition:opacity .5s ease');
  doc.documentElement.appendChild(layer);
  function lum(c){ var m = String(c).match(/[\d.]+/g); if(!m || m.length < 3) return 0;
    var f = function(v){ v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); };
    return .2126 * f(+m[0]) + .7152 * f(+m[1]) + .0722 * f(+m[2]); }
  function isDark(){
    var cs = (w.getComputedStyle(doc.documentElement).colorScheme || '').toLowerCase();
    var d = cs.indexOf('dark') >= 0, l = cs.indexOf('light') >= 0;
    if(d && !l) return true; if(l && !d) return false;
    return lum(w.getComputedStyle(doc.body || doc.documentElement).color) > .5;
  }
  var last = null;
  function update(first){
    var d = isDark(); if(d === last) return; last = d;
    if(first){ layer.style.transition = 'none'; layer.style.opacity = d ? 0 : 1; void layer.offsetWidth; layer.style.transition = 'opacity .5s ease'; }
    else layer.style.opacity = d ? 0 : 1;
  }
  update(true);
  var obs = new w.MutationObserver(function(){ update(false); });
  obs.observe(doc.documentElement, { attributes:true });
  if(doc.body) obs.observe(doc.body, { attributes:true });
  w.__recBgObs = obs;
}
