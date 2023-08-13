
const progressBars = [
  { title: "Seconde", legendId: "second-legend", progressId: "second-progress", legendText: "nog x ms" },
  { title: "Minuut", legendId: "minute-legend", progressId: "minute-progress", legendText: "nog x.y seconden" },
  { title: "Uur", legendId: "hour-legend", progressId: "hour-progress", legendText: "nog x minuten y seconden" },
  { title: "Dag", legendId: "day-legend", progressId: "day-progress", legendText: "xx.yyy%" },
  { title: "Week", legendId: "week-legend", progressId: "week-progress", legendText: "xx.yyy%" },
  { title: "Maand", legendId: "month-legend", progressId: "month-progress", legendText: "xx.yyy%" },
  { title: "Jaar", legendId: "year-legend", progressId: "year-progress", legendText: "nog xx.yyyyy%" },
  { title: "Pensioen", legendId: "pension-legend", progressId: "progress", legendText: "xx.yyyyy%" },
];

const startDate = new Date('1970-08-27T00:00:00'); 
const endDate = new Date('2037-09-01T00:00:00'); 
const daysOffPerYear = 40; 

function createTitleLegend(title, legendId, legendText) {
  const titleLegendDiv = document.createElement('div');
  titleLegendDiv.className = 'title-legend';
  const titleSpan = document.createElement('span');
  titleSpan.className = 'title';
  titleSpan.textContent = title;
  const legendSpan = document.createElement('span');
  legendSpan.id = legendId;
  legendSpan.className = 'legend';
  legendSpan.textContent = legendText;
  titleLegendDiv.appendChild(titleSpan);
  titleLegendDiv.appendChild(legendSpan);
  return titleLegendDiv;
}

function createProgressBar(progressId) {
  const progressBarDiv = document.createElement('div');
  progressBarDiv.className = 'progress-bar';
  const progressDiv = document.createElement('div');
  progressDiv.className = 'progress';
  progressDiv.id = progressId;
  progressBarDiv.appendChild(progressDiv);
  return progressBarDiv;
}

function createProgressBars() {
  progressBars.forEach(bar => {
    document.body.appendChild(createTitleLegend(bar.title, bar.legendId, bar.legendText));
    document.body.appendChild(createProgressBar(bar.progressId));
  });

  const countdownDiv = document.createElement('div');
  countdownDiv.id = 'countdown';
  countdownDiv.className = 'countdown-time';
  document.body.appendChild(countdownDiv);
}

function updateSecondCountdown() {
  const now = new Date();
  const remainingMillisecondsInSecond = 999 - now.getMilliseconds();
  const secondProgress = (now.getMilliseconds() / 1000) * 100;
  document.getElementById('second-progress').style.width = secondProgress + '%';
  document.getElementById('second-legend').textContent = `nog ${remainingMillisecondsInSecond} ms`;
}

function updateMinuteCountdown() {
  const now = new Date();
  const remainingSecondsInMinute = 59 - now.getSeconds() + (999 - now.getMilliseconds()) / 1000;
  const minuteProgress = (now.getSeconds() * 1000 + now.getMilliseconds()) / 60000 * 100;
  document.getElementById('minute-progress').style.width = minuteProgress + '%';
  document.getElementById('minute-legend').textContent = `nog ${remainingSecondsInMinute.toFixed(3)} seconden`;
}

function updateHourCountdown() {
  const now = new Date();
  const remainingMinutes = 59 - now.getMinutes();
  const remainingSeconds = 59 - now.getSeconds();

  const hourProgress = (now.getMinutes() * 60 + now.getSeconds()) / 3600 * 100;
  document.getElementById('hour-progress').style.width = hourProgress + '%';

  let legendText;
  if (remainingMinutes === 0) {
    legendText = remainingSeconds === 1 ? `nog ${remainingSeconds} seconde` : `nog ${remainingSeconds} seconden`;
  } else {
    const minutesText = remainingMinutes === 1 ? 'minuut' : 'minuten';
    const secondsText = remainingSeconds === 1 ? 'seconde' : 'seconden';
    legendText = `nog ${remainingMinutes} ${minutesText} ${remainingSeconds} ${secondsText}`;
  }

  document.getElementById('hour-legend').textContent = legendText;
}


function updateDayCountdown() {
  const now = new Date();
  const startOfDay = new Date(now);
  startOfDay.setHours(0, 0, 0, 0);
  const elapsedTime = now - startOfDay;
  const totalTime = 24 * 60 * 60 * 1000;
  const progress = (elapsedTime / totalTime) * 100;
  document.getElementById('day-progress').style.width = progress + '%';
  document.getElementById('day-legend').textContent = `${progress.toFixed(5)}%`;
}

function updateWeekCountdown() {
  const now = new Date();
  const startOfWeek = new Date(now);
  const daysUntilMonday = (now.getDay() + 6) % 7; 
  startOfWeek.setDate(now.getDate() - daysUntilMonday);
  startOfWeek.setHours(0, 0, 0, 0);
  const elapsedTime = now - startOfWeek;
  const totalTime = 7 * 24 * 60 * 60 * 1000; 
  const progress = (elapsedTime / totalTime) * 100;
  document.getElementById('week-progress').style.width = progress + '%';
  document.getElementById('week-legend').textContent = `${progress.toFixed(5)}%`;
}

function updateMonthCountdown() {
  const now = new Date();
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
  const endOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59, 999);
  const elapsedTime = now - startOfMonth;
  const totalTime = endOfMonth - startOfMonth;
  const progress = (elapsedTime / totalTime) * 100;
  document.getElementById('month-progress').style.width = progress + '%';
  document.getElementById('month-legend').textContent = `${progress.toFixed(5)}%`;
}

function updateYearCountdown() {
  const now = new Date();
  const startOfYear = new Date(now.getFullYear(), 1, 1);
  const endOfYear = new Date(now.getFullYear(), 11, 31, 23, 59, 59, 999);
  const elapsedTime = now - startOfYear;
  const totalTime = endOfYear - startOfYear;
  const progress = (elapsedTime / totalTime) * 100;
  document.getElementById('year-progress').style.width = progress + '%';
  document.getElementById('year-legend').textContent = `${progress.toFixed(7)}%`;
}

function updatePensionCountdown() {
  const now = new Date();
  const remainingTime = endDate - now;
  const totalDuration = endDate - startDate;
  const progressPast = (1 - remainingTime / totalDuration) * 100;
  const progressRemaining = 100 - progressPast; 
  document.getElementById('progress').style.width = progressPast + '%';
  document.getElementById('pension-legend').textContent = `nog ${progressRemaining.toFixed(10)}%`;
}

function calculateWorkdays(start, end) {
  let workdays = 0;
  let current = new Date(start);
  const oneYearInMilliseconds = 1000 * 60 * 60 * 24 * 365;
  const daysOff = (end - start) / oneYearInMilliseconds * daysOffPerYear;

  while (current <= end) {
    if (current.getDay() !== 0 && current.getDay() !== 6) {
      workdays++;
    }
    current.setDate(current.getDate() + 1);
  }

  workdays -= daysOff;

  return Math.max(0, workdays).toFixed();
}


function fuzzyTime() {
    const now = new Date();
    h = now.getHours();
    m = now.getMinutes();

    hours = ['middernacht', 'één', 'twee', 'drie', 'vier', 'vijf', 'zes', 'zeven', 'acht', 'negen', 'tien', 'elf', 'twaalf', 'één', 'twee', 'drie', 'vier', 'vijf', 'zes', 'zeven', 'acht', 'negen', 'tien', 'elf', 'middernacht'];
    if (m < 30) {
        x = hours[h];
    } else {
        x = hours[h + 1];
    }
    if (m == 59 || m == 0) { x += ' uur' };
    if (m == 0) { return ('exact ' + x); }
    if (m >= 1 && m <= 4) { return ('een beetje na ' + x); }
    if (m == 5) { return ('vijf na ' + x); }
    if (m >= 6 && m <= 9) { return ('bijna tien na ' + x); }
    if (m == 10) { return ('tien na ' + x); }
    if (m >= 11 && m <= 14) { return ('bijna kwart na ' + x); }
    if (m == 15) { return ('kwart na ' + x); }
    if (m >= 16 && m <= 17) { return ('kwart na ' + x + ' en een beetje'); }
    if (m >= 18 && m <= 19) { return ('bijna twintig na ' + x); }
    if (m == 20) { return ('twintig na ' + x); }
    if (m >= 21 && m <= 29) { return ('bijna half ' + x); }
    if (m == 30) { return ('half ' + x); }
    if (m >= 30 && m <= 35) { return ('een beetje na half ' + x); }
    if (m >= 36 && m <= 39) { return ('bijna twintig voor ' + x); }
    if (m == 40) { return ('twintig voor ' + x); }
    if (m >= 41 && m <= 44) { return ('ongeveer kwart voor ' + x); }
    if (m == 45) { return ('kwart voor ' + x); }
    if (m >= 46 && m <= 49) { return ('bijna tien voor ' + x); }
    if (m == 50) { return ('tien voor ' + x); }
    if (m >= 51 && m <= 54) { return ('iets na tien voor ' + x); }
    if (m == 55) { return ('vijf voor ' + x); }
    if (m >= 56 && m <= 59) { return ('bijna ' + x + ' uur'); }
}

function updateFuzzyTime() {
  const fuzzyTimeString = fuzzyTime();
  const now = new Date();
  const remainingTime = endDate - now;
  const remainingCalendarDays = Math.floor(remainingTime / (1000 * 60 * 60 * 24));
  const remainingWorkdays = calculateWorkdays(now, endDate); // Function that calculates workdays
  
  const days = ['zondag', 'maandag', 'dinsdag', 'woensdag', 'donderdag', 'vrijdag', 'zaterdag'];
  const months = ['januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli', 'augustus', 'september', 'oktober', 'november', 'december'];

  const dayName = days[now.getDay()];
  const date = now.getDate();
  const monthName = months[now.getMonth()];
  const year = now.getFullYear();

  const fullHeading = `Het is ${fuzzyTimeString} op ${dayName} ${date} ${monthName} ${year}.<br />Nog ${remainingCalendarDays} kalender- en ${remainingWorkdays} werkdagen tot uw pensioen.`;

  document.getElementById('heading').innerHTML = fullHeading;
}


function updateCountdown() {
  updateSecondCountdown();
  updateMinuteCountdown();
  updateHourCountdown();
  updateDayCountdown();
  updateWeekCountdown();
  updateMonthCountdown();
  updateYearCountdown();
  updatePensionCountdown();
  updateFuzzyTime();
}

createProgressBars();
setInterval(updateCountdown, 10);
