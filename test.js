fetch('https://jerlene-transmeridional-unrecognisably.ngrok-free.dev') // 1. 發送請求
  .then(response => { // 2. 處理 Response 物件 (包含狀態碼、Headers等)
    if (!response.ok) {
      throw new Error('HTTP 錯誤! 狀態碼: ' + response.status);
    }
    return response.json(); // 3. 解析 Response Body (例如: JSON)
  })
  .then(data => { // 4. 取得解析後的資料 (例如: JSON 轉換的物件)
    console.log(data);
  })
  .catch(error => { // 5. 錯誤處理 (網路錯誤或 response.ok 為 false)
    console.error('發生錯誤:', error);
  });
