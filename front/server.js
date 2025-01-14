const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const { spawn } = require('child_process');
const axios = require('axios'); // axios 모듈 필요
const app = express();
const server = http.createServer(app);
const io = new Server(server);
const port = 3000;

// CSV 파일 경로
const csvFilePath = path.join(__dirname, '..', 'back', 'conf.csv');
let globalInputData = null; // 단일 사용자용 글로벌 데이터

// JSON 파싱
app.use(express.json());
// 정적 파일 제공
app.use(express.static(path.join(__dirname, 'public')));
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views')); // 템플릿 파일의 디렉토리 설정

// 학회 데이터 API
app.get('/conferences', (req, res) => {
    const data = [];
    fs.createReadStream(csvFilePath)
        .pipe(csv())
        .on('data', (row) => data.push(row))
        .on('end', () => res.json(data));
});

// 메인 페이지 제공
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'homepage.html'));
});

app.post('/results', (req, res) => {
    console.log('POST /results 요청 데이터:', req.body); // 요청 데이터 확인
    const { isDictionary, data } = req.body;

    if (!data) {
        console.error('결과 데이터가 비어 있습니다.');
        return res.status(400).send('No result data received.');
    }

    // 딕셔너리인지 확인하고 EJS 템플릿 렌더링
    res.render('results', {
        pythonResult: isDictionary ? data : { error: "Not a dictionary", output: data },
    });
});



app.get('/loading', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'loading.html'));
});

app.post('/submit', (req, res) => {
    globalInputData = req.body; // 사용자 데이터 저장
    res.sendFile(path.join(__dirname, 'public', 'loading.html'));
});

// Socket.IO 연결
io.on('connection', (socket) => {
    console.log('클라이언트 연결됨.');

    socket.on('start-python', () => {
        console.log('Python 스크립트 실행 시작.');
        let pythonOutput = ''; // Python 출력 데이터 저장
    
        // Python 프로세스 실행 (버퍼링 해제)
        const pythonProcess = spawn('python', ['-u', path.join(__dirname, '..', 'back', 'PCSS_WEB.py'), JSON.stringify(globalInputData)]);
    
        // Python stdout 처리
        pythonProcess.stdout.on('data', (data) => {
            pythonOutput += data.toString();
            socket.emit('python_output', data.toString()); // 클라이언트에 실시간 전송
        });
    
        // Python stderr 처리
        pythonProcess.stderr.on('data', (data) => {
            console.error(`Python stderr: ${data}`);
            pythonOutput += data.toString();
            socket.emit('python_error', data.toString()); // 에러 출력 전송
        });
    
        pythonProcess.on('close', (code) => {
            console.log(`Python 종료. 코드: ${code}`);
            console.log(pythonOutput);
        
            try {
                // 딕셔너리 추출
                const dictStartIndex = pythonOutput.indexOf('{');
                if (dictStartIndex !== -1) {
                    const dictString = pythonOutput.slice(dictStartIndex).trim();
                    const finalOutput = JSON.parse(dictString);
        
                    // 클라이언트로 딕셔너리 데이터를 전송
                    socket.emit('redirect_to_results', { isDictionary: true, data: finalOutput });
                } else {
                    console.error('딕셔너리를 찾지 못했습니다.');
                    // 원본 문자열 데이터를 전송
                    socket.emit('redirect_to_results', { isDictionary: false, data: pythonOutput });
                }
            } catch (err) {
                console.error('JSON 파싱 에러:', err);
                // JSON 파싱 에러 발생 시 원본 데이터를 전송
                socket.emit('redirect_to_results', { isDictionary: false, data: pythonOutput.trim() });
            }
        });
        
            
        // 클라이언트가 연결 해제되면 Python 프로세스 종료
        socket.on('disconnect', () => {
            console.log('클라이언트 연결 해제.');
            pythonProcess.kill();
        });
    });    
});

// 서버 실행
server.listen(port, () => {
    console.log(`서버 실행 중: http://localhost:${port}`);
});
