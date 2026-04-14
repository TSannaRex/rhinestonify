// ─── STATE ────────────────────────────────────────────────────────────────────
var selectedFile = null;
var currentSvgData = null;

// ─── UPLOAD HANDLING ──────────────────────────────────────────────────────────
function handleFile(input) {
  var f = input.files[0];
  if (!f) return;
  selectedFile = f;
  var url = URL.createObjectURL(f);
  document.getElementById('previewImg').src = url;
  document.getElementById('uploadInner').style.display = 'none';
  document.getElementById('previewWrap').style.display = 'block';
  document.getElementById('convertBtn').disabled = false;
  document.getElementById('result-section').style.display = 'none';
  currentSvgData = null;
}

function resetUpload() {
  selectedFile = null;
  currentSvgData = null;
  document.getElementById('fileInput').value = '';
  document.getElementById('previewImg').src = '';
  document.getElementById('uploadInner').style.display = 'block';
  document.getElementById('previewWrap').style.display = 'none';
  document.getElementById('convertBtn').disabled = true;
  document.getElementById('result-section').style.display = 'none';
}

// ─── DRAG AND DROP ────────────────────────────────────────────────────────────
var zone = document.getElementById('uploadZone');
zone.addEventListener('dragover', function(e) {
  e.preventDefault();
  zone.classList.add('dragover');
});
zone.addEventListener('dragleave', function() {
  zone.classList.remove('dragover');
});
zone.addEventListener('drop', function(e) {
  e.preventDefault();
  zone.classList.remove('dragover');
  var f = e.dataTransfer.files[0];
  if (f && (f.type === 'image/jpeg' || f.type === 'image/png')) {
    var dt = new DataTransfer();
    dt.items.add(f);
    document.getElementById('fileInput').files = dt.files;
    handleFile(document.getElementById('fileInput'));
  }
});

// ─── CONVERT ──────────────────────────────────────────────────────────────────
async function convert() {
  if (!selectedFile) return;

  showLoading('Analysing your image...');
  document.getElementById('convertBtn').disabled = true;

  var stoneSizeMm   = document.getElementById('stoneSizeMm').value;
  var targetWidthMm = document.getElementById('targetWidthMm').value;
  var spacingMm     = document.getElementById('spacingMm').value;

  var fd = new FormData();
  fd.append('image', selectedFile);
  fd.append('stone_size_mm', stoneSizeMm);
  fd.append('target_width_mm', targetWidthMm);
  fd.append('spacing_mm', spacingMm);

  try {
    updateLoading('Placing rhinestones...');
    var res = await fetch('/api/generate', { method: 'POST', body: fd });
    var data = await res.json();

    if (!res.ok || data.status !== 'success') {
      throw new Error(data.error || data.detail || 'Generation failed');
    }

    updateLoading('Building your SVG...');
    currentSvgData = data.svg_data;
    showResult(data, { stoneSizeMm, targetWidthMm, spacingMm });

  } catch (e) {
    hideLoading();
    alert('Sorry, something went wrong: ' + e.message);
  } finally {
    hideLoading();
    document.getElementById('convertBtn').disabled = false;
  }
}

// ─── SHOW RESULT ──────────────────────────────────────────────────────────────
function showResult(data, params) {
  // Stone count
  var count = data.stone_count != null ? data.stone_count.toLocaleString() : '—';
  document.getElementById('stoneCountNumber').textContent = count;

  // SVG preview
  var wrap = document.getElementById('svgPreviewWrap');
  wrap.innerHTML = data.svg_data;
  // Make the SVG responsive inside the preview container
  var svg = wrap.querySelector('svg');
  if (svg) {
    svg.style.maxWidth = '100%';
    svg.style.maxHeight = '340px';
    svg.style.height = 'auto';
  }

  // Spec rows
  var ssLabel = document.getElementById('stoneSizeMm').options[document.getElementById('stoneSizeMm').selectedIndex].text;
  var specs = [
    { label: 'Stone Size', value: ssLabel },
    { label: 'Target Width', value: params.targetWidthMm + ' mm' },
    { label: 'Spacing Gap', value: params.spacingMm + ' mm' },
  ];
  var specGrid = document.getElementById('specGrid');
  specGrid.innerHTML = specs.map(function(s) {
    return '<div class="spec-row"><span class="spec-label">' + s.label + '</span><span class="spec-value">' + s.value + '</span></div>';
  }).join('');

  // Enable download
  document.getElementById('downloadBtn').disabled = false;

  // Show section
  document.getElementById('result-section').style.display = 'block';
  document.getElementById('result-section').scrollIntoView({ behavior: 'smooth' });
}

// ─── DOWNLOAD SVG ─────────────────────────────────────────────────────────────
function downloadSvg() {
  if (!currentSvgData) return;

  var blob = new Blob([currentSvgData], { type: 'image/svg+xml' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = 'rhinestone_template.svg';
  a.click();
  URL.revokeObjectURL(url);
  confetti();
}

// ─── LOADING ──────────────────────────────────────────────────────────────────
function showLoading(text) {
  document.getElementById('loadingText').textContent = text || 'Loading...';
  document.getElementById('loadingOverlay').style.display = 'flex';
}
function updateLoading(text) {
  document.getElementById('loadingText').textContent = text;
}
function hideLoading() {
  document.getElementById('loadingOverlay').style.display = 'none';
}

// ─── CONFETTI ─────────────────────────────────────────────────────────────────
function confetti() {
  var c = document.getElementById('cf');
  var cols = ['#7c5cbf', '#c9956b', '#d4c4f5', '#a8724a', '#f0ebfa', '#fdf0e8', '#5a3d9a', '#fff'];
  for (var i = 0; i < 120; i++) {
    var p = document.createElement('div');
    p.className = 'cfp';
    var sz = Math.random() * 10 + 4;
    // Mix circles and diamond shapes
    var shape = Math.random() > 0.5 ? '50%' : '2px';
    p.style.cssText = 'left:' + Math.random() * 100 + '%;width:' + sz + 'px;height:' + sz + 'px;background:' + cols[Math.floor(Math.random() * cols.length)] + ';border-radius:' + shape + ';animation-duration:' + (Math.random() * 2 + 2.5) + 's;animation-delay:' + (Math.random() * 1) + 's;transform:rotate(' + (Math.random() * 360) + 'deg)';
    c.appendChild(p);
    setTimeout(function() { if (p.parentNode) p.remove(); }, 5000);
  }
}
