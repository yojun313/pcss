const express = require('express');
const app = express();
app.use(express.json({ limit: '50mb' }));
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

// 로그 파일을 저장할 디렉토리
const logDir = path.join(__dirname, 'log');
if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir);
}

// 로그 기록 함수
function logError(errorMessage) {
    const now = new Date();
    const timestamp = now.toISOString().replace(/T/, ' ').replace(/\..+/, ''); // YYYY-MM-DD HH:MM:SS 형식
    const filename = `${now.toISOString().slice(0, 19).replace(/:/g, '-').replace('T', '_')}.txt`; // YYYY-MM-DD_HH-MM-SS.txt 형식
    const filePath = path.join(logDir, filename);

    const logEntry = `[${timestamp}] ${errorMessage}\n`;
    fs.appendFileSync(filePath, logEntry, 'utf8'); // 오류 내용을 파일에 추가

    //console.error(logEntry); // 콘솔에도 오류 출력
}

// CSV 파일 경로
const csvFilePath = path.join(__dirname, '..', 'back', 'data', 'conf.csv');
let globalInputData = null; // 단일 사용자용 글로벌 데이터

app.use(express.static(path.join(__dirname, 'public')));
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));


app.get('/loading', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'loading.html'));
});

app.get('/conferences', (req, res) => {
    const data = [];
    fs.createReadStream(csvFilePath)
        .pipe(csv())
        .on('data', (row) => data.push(row))
        .on('end', () => res.json(data))
        .on('error', (err) => logError(`CSV 파일 읽기 오류: ${err.message}`));
});

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'homepage.html'));
});

// GlobalInputData를 JSON으로 반환하는 라우트
app.get('/loading-data', (req, res) => {
    // globalInputData가 없을 때 처리 (필요 시)
    if (!globalInputData) {
        return res.json({ error: 'No input data found.' });
    }
    res.json(globalInputData);
});


app.post('/results', (req, res) => {
    const { isDictionary, data } = req.body;

    if (!data) {
        const errorMsg = '결과 데이터가 비어 있습니다.';
        logError(errorMsg);
        return res.status(400).send(errorMsg);
    }

    let pythonResult;
    if (isDictionary) {
        pythonResult = data;
    } else {
        pythonResult = { error: "Data is not in dictionary format", output: data };
    }

    // globalInputData에 저장된 옵션을 results.ejs에 전달
    res.render('results', { pythonResult, options: globalInputData, error: null });
});


app.post('/submit', (req, res) => {
    globalInputData = req.body;
    res.sendFile(path.join(__dirname, 'public', 'loading.html'));
});

io.on('connection', (socket) => {
    socket.on('start-python', () => {
        let pythonOutput = '';

        const pythonProcess = spawn('python', ['-u', path.join(__dirname, '..', 'back', 'PCSS_WEB.py'), JSON.stringify(globalInputData)]);

        pythonProcess.stdout.on('data', (data) => {
            pythonOutput += data.toString();
            socket.emit('python_output', data.toString());
        });

        pythonProcess.stderr.on('data', (data) => {
            const errorMsg = `Python stderr: ${data}`;
            logError(errorMsg);
            pythonOutput += data.toString();
            socket.emit('python_error', data.toString());
        });

        pythonProcess.on('close', (code) => {
            try {
                const pathStartIndex = pythonOutput.indexOf('PATH=');
                if (pathStartIndex !== -1) {
                    const pathEndIndex = pythonOutput.indexOf('\n', pathStartIndex);
                    const jsonPath = pythonOutput.slice(pathStartIndex + 5, pathEndIndex !== -1 ? pathEndIndex : undefined).trim();

                    if (jsonPath === "ERROR") {
                        const errorMsg = 'Python 실행 중 오류 발생';
                        logError(errorMsg);
                        socket.emit('redirect_to_results', { isDictionary: false, data: errorMsg });
                        return;
                    }

                    fs.readFile(jsonPath, 'utf-8', (err, fileData) => {
                        if (err) {
                            const errorMsg = `JSON 파일 읽기 오류: ${err.message}`;
                            logError(errorMsg);
                            socket.emit('redirect_to_results', { isDictionary: false, data: errorMsg });
                            return;
                        }

                        try {
                            const finalOutput = JSON.parse(fileData);
                            socket.emit('redirect_to_results', { isDictionary: true, data: finalOutput });

                            fs.unlink(jsonPath, (unlinkErr) => {
                                if (unlinkErr) {
                                    logError(`JSON 파일 삭제 오류: ${unlinkErr.message}`);
                                }
                            });
                        } catch (parseErr) {
                            const errorMsg = `JSON 파싱 오류: ${parseErr.message}`;
                            logError(errorMsg);
                            socket.emit('redirect_to_results', { isDictionary: false, data: errorMsg });
                        }
                    });
                } else {
                    const errorMsg = 'PATH를 포함하는 문자열을 찾을 수 없습니다.';
                    logError(errorMsg);
                    socket.emit('redirect_to_results', { isDictionary: false, data: errorMsg });
                }
            } catch (err) {
                logError(`오류 발생: ${err.message}`);
                socket.emit('redirect_to_results', { isDictionary: false, data: pythonOutput.trim() });
            }
        });

        socket.on('disconnect', () => {
            pythonProcess.kill();
        });
    });
});

server.listen(port, () => {
    console.log(`서버 실행 중: http://localhost:${port}`);
});
