/* The three tools on the Try it page. Built by neuroswitch.site_build; every
   number is computed in the browser from data delivered with the page. Nothing is
   sent anywhere and nothing is stored. */

(function () {
  const host = document.getElementById('repl');
  if (!host) return;

  // Normal quantile, Acklam's approximation. Good to about 1e-9.
  function qnorm(p) {
    const a=[-3.969683028665376e+01,2.209460984245205e+02,-2.759285104469687e+02,
             1.383577518672690e+02,-3.066479806614716e+01,2.506628277459239e+00];
    const b=[-5.447609879822406e+01,1.615858368580409e+02,-1.556989798598866e+02,
             6.680131188771972e+01,-1.328068155288572e+01];
    const c=[-7.784894002430293e-03,-3.223964580411365e-01,-2.400758277161838e+00,
             -2.549732539343734e+00,4.374664141464968e+00,2.938163982698783e+00];
    const d=[7.784695709041462e-03,3.224671290700398e-01,2.445134137142996e+00,
             3.754408661907416e+00];
    const pl=0.02425;
    let q,r;
    if (p<pl){q=Math.sqrt(-2*Math.log(p));
      return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);}
    if (p<=1-pl){q=p-0.5;r=q*q;
      return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q/(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1);}
    q=Math.sqrt(-2*Math.log(1-p));
    return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
  }
  // deterministic normal draws, so the same settings always give the same picture
  let seed = 20260824;
  function rnd(){ seed = (seed*1664525 + 1013904223) >>> 0; return (seed+0.5)/4294967296; }
  function rnorm(){ return qnorm(Math.min(Math.max(rnd(),1e-12),1-1e-12)); }

  const el = id => document.getElementById(id);
  function run() {
    const rTrue = parseFloat(el('r-true').value);
    const n = parseInt(el('r-n').value, 10);
    const studies = 4000;
    el('r-true-v').textContent = rTrue.toFixed(2);
    el('r-n-v').textContent = n;

    // Fisher z sampling distribution of a correlation
    const z = 0.5*Math.log((1+rTrue)/(1-rTrue));
    const se = 1/Math.sqrt(Math.max(n-3,1));
    const crit = 1.959963985;
    let sig=0, sumSig=0, sumAll=0, signFlip=0;
    const found=[];
    seed = 20260824;
    for (let i=0;i<studies;i++){
      const zi = z + se*rnorm();
      const ri = Math.tanh(zi);
      sumAll += ri;
      if (Math.abs(zi/se) > crit){
        sig++; sumSig += Math.abs(ri); found.push(Math.abs(ri));
        if (Math.sign(ri) !== Math.sign(rTrue) && rTrue !== 0) signFlip++;
      }
    }
    const power = sig/studies;
    const published = sig ? sumSig/sig : 0;
    const inflation = rTrue !== 0 && sig ? published/Math.abs(rTrue) : 0;

    el('r-power').textContent = (power*100).toFixed(0) + '%';
    el('r-pub').textContent = sig ? published.toFixed(2) : 'n/a';
    el('r-infl').textContent = sig ? inflation.toFixed(1) + 'x' : 'n/a';
    el('r-flip').textContent = sig ? (100*signFlip/sig).toFixed(0) + '%' : 'n/a';

    // histogram of the effects that would get published
    const bins = 30, lo = 0, hi = 1;
    const counts = new Array(bins).fill(0);
    for (const v of found) counts[Math.min(bins-1, Math.floor((v-lo)/(hi-lo)*bins))]++;
    const maxC = Math.max(...counts, 1);
    const w=620,h=190,pl=40,pr=14,pt=14,pb=36;
    const sx = v => pl + ((v-lo)/(hi-lo))*(w-pl-pr);
    const sy = c => h-pb-(c/maxC)*(h-pt-pb);
    let s=`<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img"
      aria-label="Effect sizes that would get published, from ${studies} simulated studies of ${n} people.">`;
    for (let i=0;i<bins;i++){
      if(!counts[i]) continue;
      const a=sx(lo+(hi-lo)*i/bins), b2=sx(lo+(hi-lo)*(i+1)/bins);
      s+=`<rect x="${a.toFixed(1)}" y="${sy(counts[i]).toFixed(1)}"
           width="${Math.max(1,b2-a-0.8).toFixed(1)}" height="${(h-pb-sy(counts[i])).toFixed(1)}"
           fill="var(--paper-3)" stroke="var(--rule-2)" stroke-width="0.5"/>`;
    }
    const tx = sx(Math.abs(rTrue));
    s+=`<line x1="${tx.toFixed(1)}" y1="${pt-4}" x2="${tx.toFixed(1)}" y2="${h-pb}"
         stroke="var(--right)" stroke-width="2"/>`;
    s+=`<text x="${tx.toFixed(1)}" y="${pt-6}" font-size="13" text-anchor="middle"
         fill="var(--right)" font-family="var(--sans)" font-weight="600">the truth</text>`;
    if (sig){
      const px = sx(published);
      s+=`<line x1="${px.toFixed(1)}" y1="${pt-4}" x2="${px.toFixed(1)}" y2="${h-pb}"
           stroke="var(--left)" stroke-width="2" stroke-dasharray="4 3"/>`;
      s+=`<text x="${px.toFixed(1)}" y="${h-pb+26}" font-size="13" text-anchor="middle"
           fill="var(--left)" font-family="var(--sans)" font-weight="600">what gets published</text>`;
    }
    s+=`<line x1="${pl}" y1="${h-pb}" x2="${w-pr}" y2="${h-pb}" stroke="var(--ink)"/>`;
    for (const t of [0,0.2,0.4,0.6,0.8,1.0]){
      s+=`<line x1="${sx(t)}" y1="${h-pb}" x2="${sx(t)}" y2="${h-pb+4}" stroke="var(--ink)"/>`;
      s+=`<text x="${sx(t)}" y="${h-pb+15}" font-size="13" text-anchor="middle"
           fill="var(--ink-2)" font-family="var(--sans)">${t.toFixed(1)}</text>`;
    }
    s+=`</svg>`;
    el('r-chart').innerHTML=s;

    const v = el('r-verdict');
    if (power < 0.3){
      v.className='verdict bad';
      v.innerHTML=`<p>With ${n} people and a true effect of ${rTrue.toFixed(2)}, only
        <strong>${(power*100).toFixed(0)}%</strong> of studies would find it. The ones that
        do would report it as <strong>${published.toFixed(2)}</strong> on average, which is
        <strong>${inflation.toFixed(1)} times</strong> too big. Most of the literature you
        would see from this design is wrong in size even when it is right in direction.</p>`;
    } else if (power < 0.8){
      v.className='verdict';
      v.innerHTML=`<p>${(power*100).toFixed(0)}% of studies would find this effect, and
        those that do would report it about ${inflation.toFixed(1)} times too big. Better,
        still not a design you would want to build on.</p>`;
    } else {
      v.className='verdict good';
      v.innerHTML=`<p>${(power*100).toFixed(0)}% of studies would find this, and the
        published size would be close to the truth. This is what a well-powered design
        looks like.</p>`;
    }
  }
  ['r-true','r-n'].forEach(id => el(id).addEventListener('input', run));
  run();
})();


(function () {
  const host = document.getElementById('spec');
  if (!host) return;
  const raw = document.getElementById('specdata');
  if (!raw) return;
  let D;
  try { D = JSON.parse(raw.textContent); } catch(e){ return; }
  const specs = D.specifications || [];
  if (!specs.length) return;

  const FIELDS = [
    ['condition','Which hand'], ['confounds','Confounds removed'],
    ['band','Frequency band'], ['connectivity','How links are measured'],
    ['model','Model']
  ];
  const opts = {};
  FIELDS.forEach(([f]) => { opts[f] = [...new Set(specs.map(s => s[f]))]; });

  const el = id => document.getElementById(id);
  function pick() {
    const want = {};
    FIELDS.forEach(([f]) => { want[f] = el('sp-'+f).value; });
    return specs.find(s => FIELDS.every(([f]) => s[f] === want[f])) || null;
  }

  function draw() {
    const sorted = [...specs].sort((a,b) => a.auc - b.auc);
    const chosen = pick();
    const w=640,h=230,pl=44,pr=14,pt=16,pb=40;
    const lo=Math.min(0.35,sorted[0].auc-0.02), hi=Math.max(0.9,sorted[sorted.length-1].auc+0.02);
    const sx = i => pl + (i/(sorted.length-1||1))*(w-pl-pr);
    const sy = v => h-pb-((v-lo)/(hi-lo))*(h-pt-pb);
    let s=`<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img"
      aria-label="Every one of ${sorted.length} pipelines, sorted by score. The chosen one is marked.">`;
    // chance line
    s+=`<line x1="${pl}" y1="${sy(0.5)}" x2="${w-pr}" y2="${sy(0.5)}"
         stroke="var(--ink-3)" stroke-dasharray="3 3"/>`;
    s+=`<text x="${w-pr}" y="${sy(0.5)-5}" font-size="13" text-anchor="end"
         fill="var(--ink-3)" font-family="var(--sans)">chance</text>`;
    for (let i=0;i<sorted.length;i++){
      const isPick = chosen && sorted[i] === chosen;
      s+=`<circle cx="${sx(i).toFixed(1)}" cy="${sy(sorted[i].auc).toFixed(1)}"
           r="${isPick?4.5:2}" fill="${isPick?'var(--right)':'var(--ink-3)'}"
           fill-opacity="${isPick?1:0.42}"/>`;
    }
    s+=`<line x1="${pl}" y1="${h-pb}" x2="${w-pr}" y2="${h-pb}" stroke="var(--ink)"/>`;
    s+=`<line x1="${pl}" y1="${pt}" x2="${pl}" y2="${h-pb}" stroke="var(--ink)"/>`;
    for (const t of [0.4,0.5,0.6,0.7,0.8,0.9]){
      if (t<lo||t>hi) continue;
      s+=`<text x="${pl-6}" y="${sy(t)+3.5}" font-size="13" text-anchor="end"
           fill="var(--ink-2)" font-family="var(--sans)">${t.toFixed(1)}</text>`;
    }
    s+=`<text x="${(pl+w-pr)/2}" y="${h-8}" font-size="13" text-anchor="middle"
         fill="var(--ink-2)" font-family="var(--sans)">every pipeline, worst to best</text>`;
    s+=`</svg>`;
    el('sp-chart').innerHTML=s;

    if (!chosen){
      el('sp-read').innerHTML='';
      el('sp-verdict').innerHTML='<p>That combination was not run. '+
        'Some are skipped because they do not apply, such as a graph model on the '+
        'left-minus-right difference.</p>';
      return;
    }
    const rank = sorted.indexOf(chosen)+1;
    const pct = Math.round(100*rank/sorted.length);
    el('sp-read').innerHTML =
      `<div><div class="n">${chosen.auc.toFixed(3)}</div><div class="k">AUC for this pipeline</div></div>`+
      `<div><div class="n">${rank}/${sorted.length}</div><div class="k">where it ranks</div></div>`+
      `<div><div class="n">${chosen.n}</div><div class="k">people it could use</div></div>`+
      `<div><div class="n">${D.auc_min.toFixed(3)}-${D.auc_max.toFixed(3)}</div><div class="k">full range across all pipelines</div></div>`;
    el('sp-verdict').innerHTML =
      `<p>This combination beats ${pct}% of the others. The gap between the worst and
       best defensible pipeline is <strong>${(D.auc_max-D.auc_min).toFixed(3)}</strong>
       AUC. Somebody reporting a single number from this dataset could have landed
       anywhere in that range and defended every choice along the way.</p>`;
  }

  host.querySelector('.controls').innerHTML = FIELDS.map(([f,label]) =>
    `<div class="ctl"><label for="sp-${f}">${label}</label>
     <select id="sp-${f}">${opts[f].map(o=>`<option value="${o}">${o}</option>`).join('')}</select></div>`
  ).join('');
  FIELDS.forEach(([f]) => el('sp-'+f).addEventListener('change', draw));
  draw();
})();


(async function () {
  const host = document.getElementById('brainapp');
  if (!host) return;
  let D;
  try { D = await (await fetch('data/brain.json')).json(); }
  catch (err) { host.innerHTML = '<p class="pending">Could not load the region data.</p>'; return; }
  const nodes = D.nodes.filter(n => isFinite(n.x) && isFinite(n.y) && isFinite(n.z));
  const imp = D.importance || null;
  const nets = D.networks;

  // one custom property per network, defined for both themes in style.css
  const palette = {};
  nets.forEach(n => { palette[n] = 'var(--net-' + n.toLowerCase() + ')'; });

  let active = new Set(nets), selected = null;
  const impOf = n => (imp ? (imp[n.id - 1] ?? 0) : null);
  const vals = imp ? nodes.map(impOf).filter(v => isFinite(v)) : [];
  const hi = vals.length ? Math.max(...vals) : 1, lo = vals.length ? Math.min(...vals) : 0;
  const norm = v => (hi > lo ? (v - lo) / (hi - lo) : 0.5);

  const VIEWS = [
    { a:'x', b:'y', title:'Seen from above', note:'left of the picture is the left side of the brain' },
    { a:'y', b:'z', title:'Seen from the side', note:'front of the head is on the right' }
  ];

  function svgFor(view, w, h) {
    const pad = 16;
    const xs = nodes.map(n => n[view.a]), ys = nodes.map(n => n[view.b]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs);
    const y0 = Math.min(...ys), y1 = Math.max(...ys);
    const sx = v => pad + ((v - x0) / (x1 - x0)) * (w - 2 * pad);
    const sy = v => h - pad - ((v - y0) / (y1 - y0)) * (h - 2 * pad);
    let s = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${view.title}. ${nodes.length} brain regions plotted by position.">`;
    s += `<ellipse cx="${w/2}" cy="${h/2}" rx="${w/2-pad+6}" ry="${h/2-pad+6}" fill="var(--paper-2)" stroke="var(--rule)"/>`;
    if (view.a === 'x') s += `<line x1="${w/2}" y1="${pad-6}" x2="${w/2}" y2="${h-pad+6}" stroke="var(--rule)" stroke-dasharray="3 4"/>`;
    const order = [...nodes].sort((m,n) => (imp ? norm(impOf(m)) - norm(impOf(n)) : 0));
    for (const n of order) {
      const on = active.has(n.network);
      const t = imp ? norm(impOf(n)) : 0.5;
      const r = imp ? 2.2 + t*7 : 3.4;
      const op = on ? (imp ? 0.35 + 0.65*t : 0.85) : 0.07;
      const sel = selected && selected.id === n.id;
      s += `<circle class="bnode" data-id="${n.id}" cx="${sx(n[view.a]).toFixed(1)}" cy="${sy(n[view.b]).toFixed(1)}" r="${(sel?r+3:r).toFixed(1)}" fill="${palette[n.network]}" fill-opacity="${op.toFixed(2)}" stroke="${sel?'var(--ink)':'none'}" stroke-width="1.5" tabindex="0" role="button" aria-label="${n.label}, ${n.network}"><title>${n.label}${imp?', importance '+impOf(n).toFixed(3):''}</title></circle>`;
    }
    s += `</svg>`;
    return `<figure class="bview"><div class="bviewhead">${view.title} <span>${view.note}</span></div>${s}</figure>`;
  }

  const legend = () => `<div class="legend" role="group" aria-label="Networks">` + nets.map(n =>
    `<button type="button" class="chip" data-net="${n}" aria-pressed="${active.has(n)}"><span class="sw" style="background:${palette[n]}"></span>${n}</button>`).join('')
    + `<button type="button" class="chip" data-net="__all">Show all</button></div>`;

  function detail() {
    if (!selected) return `<p>Pick a region, or use the buttons above to show one network at a time.${imp?' Bigger and more solid dots are regions the model used more.':''}</p>`;
    const n = selected;
    const side = n.hemi==='LH'?'left':n.hemi==='RH'?'right':'middle';
    return `<div class="bpick"><h3>${n.label}</h3><p>${n.network}, ${side} side, from ${n.source}, ${n.n_voxels} voxels<br>Position ${n.x}, ${n.y}, ${n.z}${imp?`<br><strong>importance ${impOf(n).toFixed(4)}</strong>`:''}</p></div>`;
  }

  function table() {
    if (!imp) return '';
    const rows = [...nodes].sort((a,b)=>impOf(b)-impOf(a)).slice(0,20).map((n,i) =>
      `<tr><td class="num">${i+1}</td><td>${n.label}</td><td>${n.network}</td><td>${n.hemi==='LH'?'left':n.hemi==='RH'?'right':'middle'}</td><td class="num">${impOf(n).toFixed(4)}</td></tr>`).join('');
    return `<h3>Regions the model used most</h3><p class="small">The same information as the map, as a list, for anyone who cannot use the picture.</p><div class="table-scroll"><table><thead><tr><th class="num">#</th><th>Region</th><th>Network</th><th>Side</th><th class="num">Importance</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function render() {
    host.innerHTML = legend() + `<div class="bgrid">${VIEWS.map(v=>svgFor(v,340,300)).join('')}</div><div id="bdetail">${detail()}</div>` + table();
    host.querySelectorAll('[data-net]').forEach(b => b.addEventListener('click', () => {
      const n = b.dataset.net;
      if (n === '__all') active = new Set(nets);
      else if (active.size === nets.length) active = new Set([n]);
      else if (active.has(n)) { active.delete(n); if (!active.size) active = new Set(nets); }
      else active.add(n);
      render();
    }));
    const pick = el => { selected = nodes.find(n => n.id === +el.dataset.id) || null; render(); };
    host.querySelectorAll('.bnode').forEach(c => {
      c.addEventListener('click', () => pick(c));
      c.addEventListener('keydown', ev => {
        if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); pick(c); }
      });
    });
  }
  render();
})();
