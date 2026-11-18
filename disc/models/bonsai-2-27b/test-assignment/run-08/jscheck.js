const fs = require('fs');
const s = fs.readFileSync('/tmp/disc_script.js', 'utf8');
try {
  new Function(s);
  console.log('JS OK');
} catch (e) {
  console.log('JS ERROR:', e.message);
  console.log('STACK:', e.stack);
}
