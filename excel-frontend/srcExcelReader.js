import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ExcelReader = () => {
    const [data, setData] = useState([]);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const response = await axios.get('http://localhost:5000/data');
            setData(response.data);
        } catch (error) {
            console.error("Ошибка загрузки данных:", error);
        }
    };

    return (
        <div>
            <h2>Данные из Excel</h2>
            <button onClick={fetchData}>Обновить данные</button>
            <table border="1">
                <thead>
                    <tr>
                        {data.length > 0 && Object.keys(data[0]).map((key) => (
                            <th key={key}>{key}</th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.map((row, index) => (
                        <tr key={index}>
                            {Object.values(row).map((value, i) => (
                                <td key={i}>{value}</td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default ExcelReader;
