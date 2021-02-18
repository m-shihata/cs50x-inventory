var date = new Date();
var today = date.toISOString().slice(0,10);
var hours = date.getHours()
var minutes = date.getMinutes()
hours = hours < 10 ? '0' + hours : hours;
minutes = minutes < 10 ? '0' + minutes : minutes;

var now = hours + ':' + minutes;
document.getElementById('today').value = today;
document.getElementById('now').value = now;