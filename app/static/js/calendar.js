document.addEventListener('DOMContentLoaded', function() {
    const calendarEl = document.getElementById('calendar');
    const schoolSelect = document.getElementById('schoolSelect');
    const facilitySelect = document.getElementById('facilitySelect');

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        locale: 'ja',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        slotMinTime: '08:00:00',
        slotMaxTime: '22:00:00',
        slotDuration: '01:00:00',
        allDaySlot: true,
        allDayText: '終日',
        height: 'auto',
        nowIndicator: true,
        buttonText: {
            today: '今日',
            month: '月',
            week: '週',
            day: '日'
        },
        events: function(info, successCallback, failureCallback) {
            const params = new URLSearchParams({
                start: info.startStr,
                end: info.endStr
            });

            const facilityId = facilitySelect.value;
            const schoolId = schoolSelect.value;

            if (facilityId) params.set('facility_id', facilityId);
            else if (schoolId) params.set('school_id', schoolId);

            fetch('/api/events?' + params.toString())
                .then(response => response.json())
                .then(data => successCallback(data))
                .catch(error => failureCallback(error));
        },
        eventClick: function(info) {
            const props = info.event.extendedProps;
            if (props.type === 'reservation') {
                alert(
                    '施設: ' + props.facility + '\n' +
                    '団体: ' + props.organization + '\n' +
                    '目的: ' + (props.purpose || '-')
                );
            } else if (props.type === 'block') {
                alert(
                    '【学校行事】\n' +
                    '施設: ' + props.facility + '\n' +
                    '理由: ' + props.reason
                );
            }
        }
    });

    calendar.render();

    // フィルター変更時にカレンダーを再読み込み
    schoolSelect.addEventListener('change', function() {
        // 学校でフィルターした施設表示
        const schoolId = this.value;
        const options = facilitySelect.querySelectorAll('option');
        options.forEach(opt => {
            if (!opt.value) return;
            if (!schoolId || opt.dataset.school === schoolId) {
                opt.style.display = '';
            } else {
                opt.style.display = 'none';
            }
        });
        facilitySelect.value = '';
        calendar.refetchEvents();
    });

    facilitySelect.addEventListener('change', function() {
        calendar.refetchEvents();
    });
});
