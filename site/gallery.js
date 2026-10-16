const $ = (id) => document.getElementById(id);
const viewer = $('viewer');
const repo = 'https://github.com/lincolnaleixo/retro-cartridge-models';
const viewOrbits = {hero:'30deg 68deg auto',front:'0deg 90deg auto',back:'180deg 90deg auto',top:'0deg 0deg auto',bottom:'0deg 180deg auto',side:'90deg 90deg auto'};
const viewNames = {hero:'Three-quarter view',photo:'Black background',front:'Front',top:'Top',bottom:'Bottom',rear:'Back',back:'Back',side:'Side',open:'Open',insert:'Removable insert'};
let catalog, selected, currentEntry, loadingTimer, activePose = 'closed', activeView = 'hero';
function chooseView(name) {
  activeView = name;
  const bounds = currentEntry?.[`${activePose}Bounds`];
  if (bounds) {
    // Frame the actual articulated envelope, including lids outside the closed box.
    const center = bounds.min.map((n, axis) => (n + bounds.max[axis]) / 2);
    const radius = Math.hypot(...bounds.dimensions) / (2 * Math.sin(Math.PI / 12)) * 1.1;
    viewer.maxCameraOrbit = `auto 180deg ${radius * 3}m`;
    viewer.cameraTarget = center.map((n) => `${n}m`).join(' ');
    viewer.cameraOrbit = viewOrbits[name].replace('auto', `${radius}m`);
  } else {
    viewer.maxCameraOrbit = 'auto 180deg auto';
    viewer.cameraTarget = 'auto auto auto';
    viewer.cameraOrbit = viewOrbits[name];
  }
  for (const button of $('views').querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.view === name));
}
function choosePose(name) {
  if (!currentEntry?.animation || !viewer.loaded) return;
  activePose = name;
  // A one-shot action clamps at the open endpoint instead of wrapping to frame zero.
  viewer.play({repetitions: 1});
  viewer.pause();
  viewer.currentTime = name === 'open' ? currentEntry.animation.durationSeconds : 0;
  for (const button of $('poses').querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.pose === name));
  chooseView(activeView);
  $('load-state').textContent = name === 'open' ? 'Open · Ready to explore' : 'Closed · Ready to explore';
}
function loadVersion(version) {
  const entry = selected.versions.find((v) => v.version === version) || selected.versions[0];
  currentEntry = entry;
  activePose = 'closed';
  $('poses').hidden = !entry.animation;
  for (const button of $('poses').querySelectorAll('button')) button.disabled = true;
  viewer.animationName = entry.animation?.name;
  viewer.animationCrossfadeDuration = 0;
  $('version').value = entry.version;
  $('load-state').textContent = 'Loading model…';
  clearTimeout(loadingTimer);
  loadingTimer = setTimeout(() => { if (!viewer.loaded) $('load-state').textContent = 'Still loading… renders are available below.'; }, 30000);
  viewer.poster = entry.previews[0].url;
  viewer.alt = `${selected.displayTitle}, version ${entry.version}. Drag or use the arrow keys to rotate.`;
  viewer.src = entry.modelUrl;
  chooseView('hero');
  $('description').textContent = selected.description;
  $('dimensions').textContent = entry.dimensions.map((n) => n.toFixed(1)).join(' × ') + ' mm · approx.';
  $('download').href = entry.releaseUrl;
  $('history').href = selected.historyUrl;
  $('credits').href = `${repo}/blob/main/${selected.credits}`;
  $('rights').textContent = selected.rights;
  $('changes').replaceChildren(...entry.changes.map((text) => { const li=document.createElement('li');li.textContent=text;return li; }));
  $('renders').replaceChildren(...entry.previews.map((preview) => {
    const link=document.createElement('a');link.className='render';link.href=preview.url;link.target='_blank';link.rel='noopener';
    const img=document.createElement('img');img.src=preview.url;img.alt=`${selected.displayTitle} — ${viewNames[preview.view] || preview.view}`;img.loading='lazy';
    const caption=document.createElement('span');caption.textContent=`${viewNames[preview.view] || preview.view} ↗`;
    link.append(img,caption);return link;
  }));
  const fragment = entry.version === selected.latest ? selected.id : `${selected.id}@${entry.version}`;
  history.replaceState(null,'',`#${fragment}`);
}
function selectAsset(id, version) {
  selected = catalog.assets.find((asset) => asset.id === id) || catalog.assets[0];
  $('explorer').hidden = false;
  $('model-title').textContent = selected.displayTitle;
  $('model-kind').textContent = selected.kind;
  $('version').replaceChildren(...selected.versions.map((entry) => {const option=document.createElement('option');option.value=entry.version;option.textContent=`v${entry.version}`;return option;}));
  document.querySelectorAll('.card').forEach((card) => card.classList.toggle('selected',card.dataset.asset === selected.id));
  loadVersion(version || selected.latest);
}
viewer.addEventListener('load', () => {
  clearTimeout(loadingTimer);
  $('load-state').textContent='Ready to explore';
  for (const button of $('poses').querySelectorAll('button')) button.disabled = false;
  choosePose('closed');
});
viewer.addEventListener('error', () => {clearTimeout(loadingTimer);$('load-state').textContent='3D loading failed. View the renders or reload the page.';});
$('views').addEventListener('click', (event) => {const button=event.target.closest('[data-view]');if(button)chooseView(button.dataset.view);});
$('poses').addEventListener('click', (event) => {const button=event.target.closest('[data-pose]');if(button)choosePose(button.dataset.pose);});
$('version').addEventListener('change', () => loadVersion($('version').value));
$('cards').addEventListener('click', (event) => {
  const link=event.target.closest('[data-explore]');if(!link || !catalog)return;
  event.preventDefault();selectAsset(link.dataset.explore);$('explorer').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
});
window.addEventListener('hashchange', () => {if(catalog){const [id,version]=location.hash.slice(1).split('@');if(catalog.assets.some((a)=>a.id===id))selectAsset(id,version);}});
try {
  const response=await fetch('gallery.json');if(!response.ok)throw new Error('Catalog unavailable');catalog=await response.json();
  $('count').textContent = `${String(catalog.assets.length).padStart(2,'0')} MODELS / VARIANTS`;
  const [id,version]=location.hash.slice(1).split('@');
  await customElements.whenDefined('model-viewer');
  selectAsset(id || 'snes-super-mario-world',version);
} catch(error) {
  $('error').hidden=false;$('error').textContent='The 3D gallery could not be loaded. Collection previews and downloads are still available above.';
  console.error(error);
}
