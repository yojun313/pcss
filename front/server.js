const express = require('express');
const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');
const { spawn } = require('child_process'); // Python 실행을 위한 spawn

const app = express();
const port = 3000;

// CSV 파일 경로
const csvFilePath = path.join(__dirname, '..', 'back', 'conf.csv');
let globalInputData = null; // 전역 변수로 inputData 저장 (단일 사용자 환경용)

// JSON 파싱
app.use(express.json());

// 정적 파일 제공
app.use(express.static(path.join(__dirname, 'public')));

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

app.get('/results', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'results.html'));
});

app.post('/submit', (req, res) => {
    globalInputData = req.body; // inputData 저장
    res.sendFile(path.join(__dirname, 'public/loading.html'));
});

app.get('/stream-python', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    let pythonOutput = ''; // Store Python stdout
    const pythonProcess = spawn('python', [path.join(__dirname, '..', 'back', 'PCSS_WEB.py'), JSON.stringify(globalInputData)]);

    pythonProcess.stdout.on('data', (data) => {
        pythonOutput += data.toString(); // Append Python output
        res.write(`data: ${data.toString()}\n\n`); // Stream output
    });

    pythonProcess.stderr.on('data', (data) => {
        res.write(`data: ERROR: ${data.toString()}\n\n`); // Stream error
    });

    pythonProcess.on('close', (code) => {
        try {
            const finalOutput = JSON.parse(pythonOutput.trim());
            const outputDict = { result: 'Python execution complete', code, finalOutput };

            // Send final output and 'complete' event
            res.write(`data: ${JSON.stringify(outputDict)}\n\n`);
            res.write(`event: complete\ndata: ${JSON.stringify(outputDict)}\n\n`); // Custom SSE event
        } catch (err) {
            const outputDict = { result: 'Python execution complete', code, finalOutput: pythonOutput.trim() };
            res.write(`data: ${JSON.stringify(outputDict)}\n\n`);
            res.write(`event: complete\ndata: ${JSON.stringify(outputDict)}\n\n`); // Custom SSE event
        }
        res.end(); // End SSE
    });
});



// 로딩 화면 HTML 반환
app.get('/loading', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'loading.html'));
});

// 서버 실행
app.listen(port, () => {
    console.log(`Server is running at http://localhost:${port}`);
});
