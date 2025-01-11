const express = require('express');
const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');

const app = express();
const port = 3000;

// CSV 파일 경로
const csvFilePath = path.join(path.join(__dirname, '..'), 'back', 'conf.csv');

// 정적 파일 제공
app.use(express.static(path.join(__dirname, 'public')));

// 학회 데이터 API
app.get('/conferences', (req, res) => {
    const data = [];
    fs.createReadStream(csvFilePath)
        .pipe(csv())
        .on('data', row => data.push(row))
        .on('end', () => res.json(data));
});

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'homepage.html'));
});


// 제출 데이터 처리
app.post('/submit', express.json(), (req, res) => {
    console.log('Submitted Data:', req.body);
    res.json({ success: true, message: 'Data received successfully!' });
});

// 서버 실행
app.listen(port, () => {
    console.log(`Server is running at http://localhost:${port}`);
});