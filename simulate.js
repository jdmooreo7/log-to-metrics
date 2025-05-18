const axios = require('axios');

async function simulateTraffic() {
  for (let i = 0; i < 100; i++) {
    try {
      await axios.get('http://localhost:3000/api/user');
      console.log(`GET Request ${i + 1} sent`);
    } catch (err) {
      console.error(`GET Request ${i + 1} failed: ${err.message}`);
    }
    try {
      await axios.post('http://localhost:3000/api/order');
      console.log(`POST Request ${i + 1} sent`);
    } catch (err) {
      console.error(`POST Request ${i + 1} failed: ${err.message}`);
    }
    await new Promise(resolve => setTimeout(resolve, 100)); // Delay 100ms
  }
}

simulateTraffic().catch(err => console.error(`Simulation failed: ${err.message}`));