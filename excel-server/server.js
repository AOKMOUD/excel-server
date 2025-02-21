const express = require('express');
const xlsx = require('xlsx');
const cors = require('cors');
const path = require('path');

const app = express();
const port = 5000;

app.use(cors()); // Разрешаем запросы с фронтенда

// Укажите путь к вашему Excel-файлу (замените на свой путь!)
const filePath = "//192.168.1.5/interview/1СУП/ООИРП/КБ/spisokKnig.xlsx"; 

// Маршрут для получения данных из Excel
app.get('/data', (req, res) => {
    try {
        const workbook = xlsx.readFile(filePath);
        const sheetName = workbook.SheetNames[0];
        const data = xlsx.utils.sheet_to_json(workbook.Sheets[sheetName]);

        res.json(data); // Отправляем данные
    } catch (error) {
        res.status(500).json({ error: 'Ошибка при чтении файла', details: error.message });
    }
});

app.listen(port, () => {
    console.log(`Сервер запущен на http://localhost:${port}`);
});
