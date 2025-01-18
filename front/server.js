const express = require('express');
const app = express();
app.use(express.json({ limit: '50mb' })); // JSON 요청 크기 제한
app.use(express.urlencoded({ limit: '50mb', extended: true }));
const http = require('http');
const { Server } = require('socket.io');
const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const { spawn } = require('child_process');

const server = http.createServer(app);
const io = new Server(server);
const port = 3000;

// CSV 파일 경로
const csvFilePath = path.join(__dirname, '..', 'back', 'conf.csv');
let globalInputData = null; // 단일 사용자용 글로벌 데이터

// 정적 파일 제공
app.use(express.static(path.join(__dirname, 'public')));
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views')); // 템플릿 파일의 디렉토리 설정

app.get('/loading', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'loading.html'));
});

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
    const { isDictionary, data } = req.body;

    // 데이터가 없는 경우 오류 처리
    if (!data) {
        console.error('결과 데이터가 비어 있습니다.');
        return res.status(400).send('No result data received.');
    }

    // `data`가 딕셔너리인지 확인
    let pythonResult;
    if (isDictionary) {
        pythonResult = data; // 딕셔너리로 정상 처리
    } else {
        pythonResult = { error: "Data is not in dictionary format", output: data };
    }

    // EJS 템플릿 렌더링
    res.render('results', { pythonResult, error: null });
});


app.post('/submit', (req, res) => {
    globalInputData = req.body; // 사용자 데이터 저장
    res.sendFile(path.join(__dirname, 'public', 'loading.html'));
});

// Socket.IO 연결
io.on('connection', (socket) => {
    socket.on('start-python', () => {
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
            try {
                // Python 출력에서 "PATH="로 시작하는 경로 추출
                const pathStartIndex = pythonOutput.indexOf('PATH=');
                if (pathStartIndex !== -1) {
                    const pathEndIndex = pythonOutput.indexOf('\n', pathStartIndex); // 줄바꿈으로 끝나는 경우
                    const jsonPath = pythonOutput
                        .slice(pathStartIndex + 5, pathEndIndex !== -1 ? pathEndIndex : undefined)
                        .trim(); // "PATH=" 이후의 경로만 가져옴
        
                    // JSON 파일 읽기
                    const fs = require('fs');
                    fs.readFile(jsonPath, 'utf-8', (err, fileData) => {
                        if (err) {
                            console.error('JSON 파일 읽기 오류:', err);
                            socket.emit('redirect_to_results', { isDictionary: false, data: `JSON 파일 읽기 오류: ${err.message}` });
                            return;
                        }
        
                        try {
                            // JSON 파일 데이터를 파싱하여 딕셔너리 생성
                            const finalOutput = JSON.parse(fileData);
        
                            // 클라이언트로 딕셔너리 데이터를 전송
                            socket.emit('redirect_to_results', { isDictionary: true, data: finalOutput });
                            fs.unlink(jsonPath, (unlinkErr) => {
                                if (unlinkErr) {
                                    console.error('JSON 파일 삭제 오류:', unlinkErr);
                                }
                            });
                        } catch (parseErr) {
                            console.error('JSON 파싱 오류:', parseErr);
                            socket.emit('redirect_to_results', { isDictionary: false, data: `JSON 파싱 오류: ${parseErr.message}` });
                        }
                    });
                } else {
                    console.error('PATH를 포함하는 문자열을 찾을 수 없습니다.');
                    socket.emit('redirect_to_results', { isDictionary: false, data: 'PATH를 포함하는 문자열을 찾을 수 없습니다.' });
                }
            } catch (err) {
                console.log('Python 출력:', pythonOutput);
                console.error('오류 발생:', err);
                socket.emit('redirect_to_results', { isDictionary: false, data: pythonOutput.trim() });
            }
        });
        
            
        // 클라이언트가 연결 해제되면 Python 프로세스 종료
        socket.on('disconnect', () => {
            pythonProcess.kill();
        });
    });    
});

// 서버 실행
server.listen(port, () => {
    console.log(`서버 실행 중: http://localhost:${port}`);
});
