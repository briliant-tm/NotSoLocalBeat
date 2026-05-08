const urlParams = new URLSearchParams(window.location.search);
const TOTAL_QUESTIONS = parseInt(urlParams.get('count')) || 10;
const MODE = urlParams.get('mode') || 'CLASSIC';
const IS_MULTIPLAYER = document.currentScript?.getAttribute('data-multiplayer') === 'true' || window.location.pathname === '/game/multiplayer';
const ROOM_ID = window.sessionStorage.getItem('current_room_id') || null;

let currentQ = 0;
let score = 0;
let replays = 3;
let isPlaying = false;
let nextData = null;
let isReady = false;
let gameStarted = false;

// Elements
const audio = document.getElementById('game-audio');
const overlayCount = document.getElementById('overlay-countdown');
const overlayOver = document.getElementById('overlay-gameover');
const overlayReady = document.getElementById('overlay-ready');
const countTxt = document.getElementById('countdown-text');
const replayBtn = document.getElementById('btn-replay');
const progressFill = document.getElementById('progress-fill');
const container = document.getElementById('game-interface-container');

// Audio Visualizer Context
let audioCtx, analyser, source, animId;
const canvas = document.getElementById('visualizer-canvas');
const ctx = canvas.getContext('2d');

// Multiplayer polling
let pollInterval = null;
let room = null;

window.onload = () => {
    document.getElementById('q-total').innerText = TOTAL_QUESTIONS;
    
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioCtx.createAnalyser();
    source = audioCtx.createMediaElementSource(audio);
    source.connect(analyser);
    analyser.connect(audioCtx.destination);
    analyser.fftSize = 256;

    if (IS_MULTIPLAYER && ROOM_ID) {
        initMultiplayer();
    } else {
        loadNextLevel();
    }
};

// ====== MULTIPLAYER FUNCTIONS ======

function initMultiplayer() {
    fetch(`/api/room/${ROOM_ID}`)
        .then(r => r.json())
        .then(data => {
            room = data;
            document.getElementById('multiplayer-info').style.display = 'block';
            document.getElementById('room-code-display').textContent = data.room_code;
            updatePlayersList();
            
            if (room.is_started) {
                loadNextLevel();
            } else {
                showReadyScreen();
            }

            pollInterval = setInterval(pollRoomStatus, 1000);
        });
}

function pollRoomStatus() {
    fetch(`/api/room/${ROOM_ID}`)
        .then(r => r.json())
        .then(data => {
            room = data;
            updatePlayersList();
            
            if (data.is_started && !gameStarted) {
                gameStarted = true;
                overlayReady.style.display = 'none';
                loadNextLevel();
            }
        })
        .catch(() => {});
}

function updatePlayersList() {
    if (!room) return;
    
    const playersList = document.getElementById('players-list');
    playersList.innerHTML = '';
    
    room.players.forEach(p => {
        const playerDiv = document.createElement('div');
        playerDiv.style.fontSize = '0.8rem';
        playerDiv.style.color = p.is_ready ? '#00ff88' : '#ff0055';
        playerDiv.style.margin = '5px 0';
        playerDiv.textContent = (p.is_host ? '[HOST] ' : '') + p.username + (p.is_ready ? ' - READY' : ' - WAITING');
        playersList.appendChild(playerDiv);
    });
    
    const readyPlayers = document.getElementById('ready-players');
    if (readyPlayers) {
        const ready = room.players.filter(p => p.is_ready).length;
        readyPlayers.innerHTML = `${ready} / ${room.players.length} players ready`;
    }
}

function showReadyScreen() {
    if (!IS_MULTIPLAYER) return;
    
    overlayReady.style.display = 'flex';
    updatePlayersList();
    
    const isHost = room && room.players.some(p => p.is_host && p.username === window.currentUsername);
    const readyBtn = document.getElementById('ready-btn');
    
    if (!isHost) {
        readyBtn.textContent = isReady ? 'UNREADY' : 'READY UP';
    } else {
        if (!document.getElementById('start-game-btn')) {
            const startBtn = document.createElement('button');
            startBtn.id = 'start-game-btn';
            startBtn.className = 'btn-main';
            startBtn.textContent = 'START GAME';
            startBtn.onclick = startMultiplayerGame;
            readyBtn.parentNode.insertBefore(startBtn, readyBtn.nextSibling);
            readyBtn.style.display = 'none';
        }
    }
}

function toggleReady() {
    isReady = !isReady;
    
    fetch(`/api/room/${ROOM_ID}/ready`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_ready: isReady })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            document.getElementById('ready-btn').textContent = isReady ? 'UNREADY' : 'READY UP';
            updatePlayersList();
        }
    })
    .catch(() => {});
}

function startMultiplayerGame() {
    fetch(`/api/room/${ROOM_ID}/start`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                gameStarted = true;
                overlayReady.style.display = 'none';
                loadNextLevel();
            } else {
                alert(data.error || 'Cannot start game');
            }
        });
}

// ====== QUIZ FUNCTIONS ======

function loadNextLevel() {
    if (currentQ >= TOTAL_QUESTIONS) {
        document.getElementById('final-score').innerText = score;
        
        if (IS_MULTIPLAYER && room) {
            const leaderboard = document.getElementById('final-leaderboard');
            leaderboard.innerHTML = '<div style="font-size: 0.9rem; margin-top: 10px;">ROOM: ' + room.room_code + '</div>';
        }
        
        overlayOver.style.display = 'flex';
        clearInterval(pollInterval);
        return;
    }

    const glitch = document.getElementById('glitch-layer');
    glitch.classList.add('glitch-active');
    setTimeout(() => glitch.classList.remove('glitch-active'), 300);

    overlayCount.style.display = 'flex';
    let timer = 3;
    countTxt.innerText = timer;
    
    const params = new URLSearchParams();
    params.append('room_id', ROOM_ID || '');
    params.append('is_multiplayer', IS_MULTIPLAYER);
    
    fetch('/api/question?' + params)
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert('Error loading question');
                return;
            }
            nextData = data;
            audio.src = `/stream_audio?type=quiz&t=${Date.now()}`;
            audio.load();
        })
        .catch(e => {
            console.error('Error:', e);
            alert('Error loading question');
        });

    const interval = setInterval(() => {
        timer--;
        if(timer > 0) countTxt.innerText = timer;
        else {
            clearInterval(interval);
            overlayCount.style.display = 'none';
            setupRound();
        }
    }, 1000);
}

function setupRound() {
    currentQ++;
    document.getElementById('q-current').innerText = currentQ;
    replays = 3;
    updateReplayBtn();
    
    document.getElementById('clue-text').innerText = nextData.clue;
    document.getElementById('mode-badge').innerText = nextData.mode;
    
    container.innerHTML = '';
    
    if (MODE === 'CLASSIC') {
        const grid = document.createElement('div');
        grid.className = 'options-grid';
        nextData.options.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.innerText = opt;
            btn.onclick = () => fadeOutAndSubmit(opt, btn);
            grid.appendChild(btn);
        });
        container.appendChild(grid);
    } 
    else if (MODE === 'TYPING') {
        const wrapper = document.createElement('div');
        wrapper.className = 'typing-container';
        
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'typing-input';
        
        if (nextData.typing_type === 'FOLDER') {
            input.placeholder = "Guess the folder name";
            input.style.borderColor = "#ff0055";
        } else {
            input.placeholder = "Type title or artist...";
        }
        
        input.onkeydown = (e) => { if(e.key === 'Enter') fadeOutAndSubmit(input.value, input); };
        
        wrapper.appendChild(input);
        container.appendChild(wrapper);
        setTimeout(() => input.focus(), 100);
    }

    playAudio();
}

function playAudio() {
    if(replays <= 0) return;
    if(audioCtx.state === 'suspended') audioCtx.resume();
    
    audio.currentTime = nextData.start_time;
    audio.volume = 0;
    audio.play();
    
    let vol = 0;
    const fade = setInterval(()=>{
        if(vol < 1.0) { vol+=0.1; audio.volume = Math.min(1,vol); }
        else clearInterval(fade);
    }, 50);

    isPlaying = true;
    replayBtn.disabled = true;
    replayBtn.innerText = "LISTENING...";
    
    cancelAnimationFrame(animId);
    updateGameLoop();
}

function updateGameLoop() {
    if(!isPlaying) return;
    
    const duration = 15;
    const elapsed = audio.currentTime - nextData.start_time;
    let pct = (elapsed / duration) * 100;
    
    if (pct >= 100 || audio.ended) {
        pct = 100; audio.pause(); handleClipEnd();
    }
    progressFill.style.width = `${pct}%`;

    const buffer = analyser.frequencyBinCount;
    const data = new Uint8Array(buffer);
    analyser.getByteFrequencyData(data);

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    ctx.clearRect(0,0,canvas.width,canvas.height);

    const barW = (canvas.width / buffer) * 4;
    const centerY = canvas.height / 2;
    let totalE = 0;

    ctx.fillStyle = '#FFFFFF';
    ctx.shadowColor = '#000'; 
    ctx.shadowBlur = 10;

    for(let i=0; i<buffer; i++) {
        let h = data[i] * 1.5;
        totalE += data[i];
        if (h > 0) {
            const x = (canvas.width/2) + (i*barW/2) * (i%2===0 ? 1 : -1); 
            ctx.fillRect(x, centerY - h/2, barW-2, h);
        }
    }

    const intensity = totalE / (buffer * 255);
    document.getElementById('dynamic-bg').style.background = 
        `radial-gradient(circle at center, rgba(30,30,30,${intensity}) 0%, #000 100%)`;

    animId = requestAnimationFrame(updateGameLoop);
}

function handleClipEnd() {
    replays--;
    isPlaying = false;
    updateReplayBtn();
}

function updateReplayBtn() {
    if(replays <= 0) {
        replayBtn.innerText = "NO MORE PLAYS (0)";
        replayBtn.disabled = true;
    } else {
        replayBtn.innerText = `REPLAY (${replays})`;
        replayBtn.disabled = false;
    }
}

function triggerReplay() { playAudio(); }

function fadeOutAndSubmit(ans, uiElement) {
    if (isPlaying) {
        if (MODE === 'CLASSIC') document.querySelectorAll('.option-btn').forEach(b=>b.disabled=true);
        if (MODE === 'TYPING') uiElement.disabled = true;

        let vol = audio.volume;
        const fade = setInterval(() => {
            if(vol > 0.05) { vol -= 0.1; audio.volume = vol; }
            else {
                clearInterval(fade);
                audio.pause();
                isPlaying = false;
                submit(ans, uiElement);
            }
        }, 50);
    } else {
        submit(ans, uiElement);
    }
}

function submit(ans, uiElement) {
    const submitData = {
        answer: ans,
        game_mode: MODE,
        typing_type: nextData.typing_type,
        source: nextData.source || 'LOCAL'
    };

    fetch('/submit_answer', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(submitData)
    })
    .then(r=>r.json())
    .then(data => {
        if(MODE === 'CLASSIC') {
            if(data.correct) { uiElement.classList.add('correct'); score += 100; }
            else { uiElement.classList.add('wrong'); }
        } 
        else if (MODE === 'TYPING') {
            if(data.score > 0) {
                uiElement.style.borderColor = "#00ff88";
                uiElement.style.color = "#00ff88";
                uiElement.value = `+${data.score}`;
                score += data.score;
            } else {
                uiElement.style.borderColor = "#ff0055";
                uiElement.style.color = "#ff0055";
                uiElement.value = "WRONG";
            }
        }
        document.getElementById('score-display').innerText = score;
        setTimeout(loadNextLevel, 2000);
    })
    .catch(e => {
        console.error('Submit error:', e);
        setTimeout(loadNextLevel, 2000);
    });
}

window.addEventListener('beforeunload', () => {
    if (pollInterval) clearInterval(pollInterval);
});