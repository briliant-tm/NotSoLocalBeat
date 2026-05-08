let audioCtx, analyser, source;
const audioEl = document.getElementById('bgm-player');
const canvas = document.getElementById('visualizer-canvas');
const ctx = canvas.getContext('2d');
const notif = document.getElementById('jukebox-notif');
const bg = document.getElementById('dynamic-bg');

let isInitialized = false;
let particles = [];

function initExperience() {
    if (isInitialized) return;
    document.getElementById('overlay-start').style.opacity = '0';
    setTimeout(() => document.getElementById('overlay-start').style.display = 'none', 500);

    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioCtx.createAnalyser();
    source = audioCtx.createMediaElementSource(audioEl);
    source.connect(analyser);
    analyser.connect(audioCtx.destination);
    analyser.fftSize = 512;

    for(let i=0; i<30; i++) particles.push({
        x: Math.random()*window.innerWidth, y: Math.random()*window.innerHeight,
        speed: Math.random()*0.5 + 0.1, size: Math.random()*2
    });

    playNextBGM();
    renderFrame();
    isInitialized = true;
}

function playNextBGM() {
    fetch('/api/bgm').then(r=>r.json()).then(data => {
        if(data.error) return;
        audioEl.src = `/stream_audio?type=bgm&token=${data.token}`;
        audioEl.currentTime = data.start;
        audioEl.volume = 0;
        audioEl.play();
        
        let vol = 0;
        let fade = setInterval(()=>{
            if(vol < 0.5) { vol+=0.05; audioEl.volume = vol; }
            else clearInterval(fade);
        }, 100);

        if (document.getElementById('bgm-title')) {
            document.getElementById('bgm-title').innerText = data.title;
            notif.classList.add('show');
            setTimeout(()=>notif.classList.remove('show'), 4000);
        }
    }).catch(() => {});
}

audioEl.onended = playNextBGM;

function renderFrame() {
    requestAnimationFrame(renderFrame);
    const buffer = analyser.frequencyBinCount;
    const data = new Uint8Array(buffer);
    analyser.getByteFrequencyData(data);

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    ctx.clearRect(0,0,canvas.width,canvas.height);

    ctx.fillStyle = 'rgba(255,255,255,0.2)';
    particles.forEach(p => {
        p.y -= p.speed; if(p.y < 0) p.y = canvas.height;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.size, 0, Math.PI*2); ctx.fill();
    });

    let totalEnergy = 0;
    const barW = (canvas.width / buffer) * 2;
    const centerY = canvas.height / 2;

    ctx.fillStyle = '#FFFFFF';
    ctx.shadowBlur = 0;

    for(let i=0; i<buffer; i++) {
        let h = data[i] * 0.8;
        totalEnergy += data[i];
        if(h > 0) {
            ctx.fillRect((i*barW) + (canvas.width/2 - (buffer*barW)/2), centerY - h/2, barW-1, h);
        }
    }

    const intensity = totalEnergy / (buffer * 255);
    const hue = 240 + (intensity * 60);
    bg.style.background = `radial-gradient(circle at center, hsla(${hue}, 60%, 10%, ${0.5 + intensity}) 0%, #000 100%)`;
}