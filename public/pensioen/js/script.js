function startTime() {

    //start of day (hours, minutes)
    var startOfDay = toMs(8, 30);

    //end  of day (hours, minutes)
    var endOfDay = toMs(17, 0);

    //noon break (hours, minutes)
    var noonBreak = toMs(12, 5);

    //birth date (year, month, day)
    var birthDate = new Date(1970, 7, 27);

    //pension age (years)
    var pensionAge = 67;


    var now = new Date();
    var yy = now.getFullYear();
    var mm = now.getMonth() + 1;
    var dd = now.getDate();
    var d = now.getDay();
    var h = now.getHours();
    var m = now.getMinutes();
    var s = now.getSeconds();
    var ms = now.getMilliseconds();

    var t = setTimeout(startTime, 1);

    var startOfYear = new Date(yy, 1, 1, 0, 0, 0, 1) - 1;
    var endOfYear = new Date(yy + 1, 1, 1, 0, 0, 0, 0) - 1;
    var pensionDate = new Date(birthDate.getFullYear() + pensionAge, birthDate.getMonth(), birthDate.getDate());

    $('#now').html('Het is ' + fuzzyTime(h, m) + ' op ' + dateFormat(now) + '.<br/> Nog ' + parseInt(daysBetween(now, pensionDate)) + ' dagen tot uw pensioen.');
    makeBar('milliseconds2', 'Seconde', 0, 1000, ms, '', '', 'ms', 'square');
    makeBar('seconds', 'Minuut', 0, toMs(0, 1), toMs(0, 0, s, ms), '', '', 's.ms', 'none');
    makeBar('minutes', 'Uur', 0, toMs(1, 0), toMs(0, m, s, ms), '', '', 'm:s', 'none');
    makeBar('day', 'Dag', toMs(0, 0), toMs(24, 0), toMs(h, m, s, ms), '', '', 'percentage', 'none');
    if (toMs(h, m, s, ms) >= startOfDay && toMs(h, m, s, ms) <= endOfDay) {
        if (toMs(h, m, s, ms) <= noonBreak) {
            makeBar('morning', 'Schaft', startOfDay, noonBreak, toMs(h, m, s, ms), '', '', 'h:m', 'none');
        } else {
            hideBar('morning');
        }
        makeBar('workday', 'Werkdag', startOfDay, endOfDay, toMs(h, m, s, ms), '', '', 'percentageleft', 'none');
        makeBar('workweek', 'Werkweek', 0, (endOfDay - startOfDay) * 5, (endOfDay - startOfDay) * (d - 1) + (toMs(h, m, s, ms) - startOfDay), '', '', 'percentageleft', 'none');
    } else {
        if (toMs(h, m, s, ms) < startOfDay) {
            day = d - 1;
        } else {
            day = d;
        }
        if (d == 0 || d > 5 || (d == 5 && toMs(h, m, s, ms) >= endOfDay)) {
            hideBar('workweek');
        } else {
            makeBar('workweek', 'Werkweek', 0, (endOfDay - startOfDay) * 5, (endOfDay - startOfDay) * day, '', '', 'percentageleft', 'none');
        }
        hideBar('workday');
    }
    makeBar('week', 'Week', toMs(0, 0), toMs(24, 0) * 7, toMs(24, 0) * (d - 1) + toMs(h, m, s, ms), '', '', 'percentageleft', 'none', 6);
    makeBar('month', 'Maand', toMs(0, 0), toMs(24, 0) * daysInMonth(now), toMs(24, 0) * (dd - 1) + toMs(h, m, s, ms), '', '', 'percentageleft', 'none', 7);
    makeBar('year', 'Jaar', startOfYear, endOfYear, now, '', '', 'percentageleft', 'none', 8);
    makeBar('pension', 'Pensioen', birthDate, pensionDate - birthDate, now - birthDate, '', '', 'percentage', 'none', 10);

}

function hideBar(id) {
    thisID = '#' + id;
    if ($(thisID).length) {
        $(thisID).hide();
    }
}

function makeBar(id, label, start, end, now, startLabel, endLabel, format, ease, precision) {
    /*
        Gegeven: 
            - #id
            - algemeen label
            - start (ms)
            - end (ms)
            - now
            - start label
            - end label
            - format: s.ms, ...
            - ease: 'square', ...
        Maak:
            - balk leeg
            - daarover balk vol tot perc
            - op perc bol met glow
            - boven links label
            - boven rechts percentage
            - onder links begin
            - onder rechts einde
    */

    thisID = '#' + id;
    percentagedone = (now - start) / (end - start) * 100;

    switch (ease) {
        case 'square':
            percentagedone = Math.pow(percentagedone, 2) / 100;
            break;
        case 'cubic':
            percentagedone = Math.pow(percentagedone, 3) / 10000;
            break;
        default:
    }
    percentagedone = percentagedone.toPrecision(5) + '%';

    donelabel = formatDoneLabel(format, end, start, now, precision);

    if ($(thisID).length) {
        $(thisID).show();
        $(thisID + ' .percentagedone').css('width', percentagedone);
        $(thisID + ' .label .right').text(donelabel);
    } else {
        bar = '<div id="' + id + '" class="progress"></div>';
        $('#content').append(bar);
        $(thisID).append('<div class="label"><div class="left">' + label + '</div><div class="right">' + donelabel + '</div>');
        $(thisID).append('<div class="total"><div class="percentagedone"></div></div></div>');
    }
}

function formatDoneLabel(format, end, start, now, precision) {
    if (!precision) precision = 5;
    ms = end - now;
    switch (format) {
        case 'ms':
            donelabel = ms;
            donelabel = 'nog ' + doPad(donelabel, 3) + ' ms ';
            break;
        case 's.ms':
            s = parseInt(ms / 1000);
            ms -= s * 1000;
            donelabel = 'nog ' + s + '.' + doPad(ms, 3) + ' seconden';
            break;
        case 'h:m':
            h = parseInt(ms / (60 * 60 * 1000));
            ms -= h * 60 * 60 * 1000;
            m = parseInt(ms / (60 * 1000));
            ms -= m * 60 * 1000;
            donelabel = 'nog ';
            if (h > 0) { donelabel += h + ' uur '; }
            donelabel += m + ' ';
            donelabel += checkPlural('minuut|minuten', m);
            break;
        case 'h:m:s':
            h = parseInt(ms / (60 * 60 * 1000));
            ms -= h * 60 * 60 * 1000;
            m = parseInt(ms / (60 * 1000));
            ms -= m * 60 * 1000;
            s = parseInt(ms / 1000);
            donelabel = 'nog ';
            if (h > 0) { donelabel += h + ' uur '; }
            if (m > 0) {
                donelabel += m + ' ';
                donelabel += checkPlural('minuut|minuten', m);
            }
            donelabel += ' ' + s + ' ';
            donelabel += checkPlural('seconde|seconden', s);
            break;
        case 'm:s':
            m = parseInt(ms / (60 * 1000));
            ms -= m * 60 * 1000;
            s = parseInt(ms / 1000);
            donelabel = 'nog ';
            if (m > 0) {
                donelabel += m + ' ';
                donelabel += checkPlural('minuut|minuten', m);
            }
            donelabel += ' ' + s + ' ';
            donelabel += checkPlural('seconde|seconden', s);
            break;
        case 'percentageleft':
            donelabel = 100 - (now - start) / (end - start) * 100;
            donelabel = 'nog ' + donelabel.toPrecision(precision) + '%';
            break;
        default:
            donelabel = now / (end - start) * 100;
            donelabel = donelabel.toPrecision(precision) + '%'
    }
    return donelabel;
}


function fuzzyTime(h, m) {
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
    if (m >= 56 && m <= 59) { return ('bijna ' + x); }
}

function dateFormat(date) {
    var montharray = new Array('januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli', 'augustus', 'september', 'oktober', 'november', 'december');
    var dayarray = new Array('zondag', 'maandag', 'dinsdag', 'woensdag', 'donderdag', 'vrijdag', 'zaterdag');
    return (dayarray[date.getDay()] + ' ' + date.getDate() + ' ' + montharray[date.getMonth()] + ' ' + date.getFullYear());
}

function daysInMonth(date) {
    return new Date(date.getYear(),
        date.getMonth() + 1,
        0).getDate();
}

function treatAsUTC(date) {
    var result = new Date(date);
    result.setMinutes(result.getMinutes() - result.getTimezoneOffset());
    return result;
}

function daysBetween(startDate, endDate) {
    var millisecondsPerDay = 24 * 60 * 60 * 1000;
    return (treatAsUTC(endDate) - treatAsUTC(startDate)) / millisecondsPerDay;
}

function toMs(h, m, s, ms) {
    ret = 0;
    if (ms) { ret += ms; }
    if (s) { ret += s * 1000; }
    ret += m * 60 * 1000;
    ret += h * 60 * 60 * 1000;
    return ret;
}

function doPad(i, ln) {
    return i.toString().length < ln ? "0".repeat(ln - i.toString().length) + i : i;
}

function checkPlural(options, nbr) {
    options = options.split('|');
    if (nbr == 1) { return options[0]; } else { return options[1]; }
}