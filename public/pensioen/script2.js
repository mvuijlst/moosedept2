
const progressBars = [
  { title: "Werkdag", legendId: "workday-legend", progressId: "workday-progress", legendText: "xx.yyy%" },
  { title: "Dag", legendId: "day-legend", progressId: "day-progress", legendText: "xx.yyy%" },
  { title: "Werkweek", legendId: "workweek-legend", progressId: "workweek-progress", legendText: "nog x uur y minuten z seconden" },
  { title: "Week", legendId: "week-legend", progressId: "week-progress", legendText: "xx.yyy%" },
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

function formatRemainingTime(days, hours, minutes, seconds) {
  let formattedTime = 'nog ';

  if (days > 0) {
    formattedTime += days === 1 ? `${days} dag ` : `${days} dagen `;
  }
  if (hours > 0) {
    formattedTime += `${hours} uur `;
  }
  if (minutes > 0) {
    formattedTime += minutes === 1 ? `${minutes} minuut ` : `${minutes} minuten `;
  }
  if (seconds > 0) {
    formattedTime += seconds === 1 ? `${seconds} seconde` : `${seconds} seconden`;
  }

  return formattedTime.trim();
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

function updateWorkdayCountdown() {
  const now = new Date();
  const startWork = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 9, 0, 0);
  const middayBreakStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 12, 30, 0);
  const middayBreakEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 12, 54, 0);
  const endWork = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 17, 0, 0);

  const totalMinutesPerDay = 7.6 * 60;

  // Update legend based on time
  if (now < startWork) {
    document.getElementById('workday-legend').textContent = "nog geen werkdag";
    return;
  } else if (now > endWork) {
    document.getElementById('workday-legend').textContent = "geen werkdag meer";
    return;
  }

  // If it's outside of working hours but within the workday, fix the progress bar to the time remaining when work stopped
  let minutesElapsedToday = ((now - startWork) / (1000 * 60));
  if (now > middayBreakStart && now < middayBreakEnd) {
    minutesElapsedToday = (middayBreakStart - startWork) / (1000 * 60);
  } else if (now > middayBreakEnd) {
    minutesElapsedToday -= (middayBreakEnd - middayBreakStart) / (1000 * 60);
  }

  const remainingMinutes = totalMinutesPerDay - minutesElapsedToday;
  const percentage = (minutesElapsedToday / totalMinutesPerDay) * 100;
  const remainingHours = Math.floor(remainingMinutes / 60);
  const remainingMinutesOnly = Math.floor(remainingMinutes % 60);
  const remainingSeconds = Math.floor((remainingMinutes * 60) % 60);

  document.getElementById('workday-progress').style.width = percentage + '%';
  document.getElementById('workday-legend').textContent = formatRemainingTime(0, remainingHours, remainingMinutesOnly, remainingSeconds);
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

function updateWorkweekCountdown() {
  const now = new Date();
  const startWork = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 9, 0, 0);
  const middayBreakStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 12, 30, 0);
  const middayBreakEnd = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 12, 54, 0);
  const endWork = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 17, 0, 0);

  const startOfWeek = new Date(now.getFullYear(), now.getMonth(), now.getDate() - now.getDay() + 1, 9, 0, 0);  // Monday 09:00
  const endOfWeek = new Date(now.getFullYear(), now.getMonth(), now.getDate() - now.getDay() + 5, 17, 0, 0);  // Friday 17:00

  const totalMinutesPerDay = 7.6 * 60;  // 7.6 hours = 456 minutes
  const totalWorkweekMinutes = 5 * totalMinutesPerDay;

  // If it's before the start of the workweek or after the end, update the legend and exit
  if (now < startOfWeek || now > endOfWeek) {
    document.getElementById('workweek-legend').textContent = "weekend!";
    return;
  }

  // If it's outside of working hours on a weekday, fix the progress bar to the time remaining when work stopped
  if ((now < startWork || (now > middayBreakStart && now < middayBreakEnd) || now > endWork) && now.getDay() > 0 && now.getDay() < 6) {
    // Calculate time as of the end of the last working period
    let referenceTime = now < startWork ? startWork : (now > endWork ? endWork : middayBreakStart);
    let daysElapsed = (now.getDay() - 1) * totalMinutesPerDay;
    let minutesElapsedToday = ((referenceTime - startWork) / (1000 * 60));
    if (referenceTime > middayBreakStart && referenceTime <= middayBreakEnd) {
        minutesElapsedToday = (middayBreakStart - startWork) / (1000 * 60);
    } else if (referenceTime > middayBreakEnd) {
        minutesElapsedToday -= (middayBreakEnd - middayBreakStart) / (1000 * 60);
    }
    const totalMinutesElapsed = daysElapsed + minutesElapsedToday;
    const remainingMinutes = totalWorkweekMinutes - totalMinutesElapsed;
    const percentage = (totalMinutesElapsed / totalWorkweekMinutes) * 100;
    const remainingHours = Math.floor(remainingMinutes / 60);
    const remainingMinutesOnly = Math.floor(remainingMinutes % 60);
    const remainingSeconds = Math.floor((remainingMinutes * 60) % 60);

    document.getElementById('workweek-progress').style.width = percentage + '%';
    document.getElementById('workweek-legend').textContent = formatRemainingTime(0, remainingHours, remainingMinutesOnly, remainingSeconds);
    return;  // Exit after fixing the progress bar to the last working time
  }

  // Make sure the progress bar is visible
  document.getElementById('workweek-progress').style.display = 'block';

  // Calculate elapsed time
  const daysElapsed = (now.getDay() - 1) * totalMinutesPerDay;  // -1 because getDay() returns 1 for Monday
  let minutesElapsedToday = ((now - startWork) / (1000 * 60));
  if (now > middayBreakStart && now < middayBreakEnd) {
    minutesElapsedToday = (middayBreakStart - startWork) / (1000 * 60);
  } else if (now > middayBreakEnd) {
    minutesElapsedToday -= (middayBreakEnd - middayBreakStart) / (1000 * 60);
  }

  const totalMinutesElapsed = daysElapsed + minutesElapsedToday;
  const remainingMinutes = totalWorkweekMinutes - totalMinutesElapsed;

  const percentage = (totalMinutesElapsed / totalWorkweekMinutes) * 100;
  const remainingHours = Math.floor(remainingMinutes / 60);
  const remainingMinutesOnly = Math.floor(remainingMinutes % 60);
  const remainingSeconds = Math.floor((remainingMinutes * 60) % 60);

  // Update progress bar and legend
  document.getElementById('workweek-progress').style.width = percentage + '%';
  document.getElementById('workweek-legend').textContent = formatRemainingTime(0, remainingHours, remainingMinutesOnly, remainingSeconds);
}



function updateCountdown() {
  updateWorkdayCountdown();
  updateDayCountdown();
  updateWorkweekCountdown();
  updateWeekCountdown();
}

createProgressBars();
setInterval(updateCountdown, 1000);
