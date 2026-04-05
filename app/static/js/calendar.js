document.addEventListener('DOMContentLoaded', function() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) return;

    const schoolSelect = document.getElementById('schoolSelect');
    const facilitySelect = document.getElementById('facilitySelect');
    const viewSwitcher = document.getElementById('viewSwitcher');
    const eventModal = new bootstrap.Modal(document.getElementById('eventModal'));

    // FullCalendar初期化
    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        locale: 'ja',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: ''
        },
        // 年間表示用のマルチマンス設定
        multiMonthMaxColumns: 3,
        // タイムグリッド設定
        slotMinTime: '08:00:00',
        slotMaxTime: '22:00:00',
        slotDuration: '01:00:00',
        slotLabelFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
        allDaySlot: true,
        allDayText: '終日',
        height: 'auto',
        nowIndicator: true,
        navLinks: true,
        dayMaxEvents: 4,
        moreLinkText: function(num) { return '+' + num + '件'; },
        // 日本語ボタン
        buttonText: {
            today: '今日',
            month: '月間',
            week: '週間',
            day: '日別',
            year: '年間'
        },
        // ビュー別設定
        views: {
            multiMonthYear: {
                type: 'multiMonth',
                duration: { months: 12 },
                buttonText: '年間',
                multiMonthMaxColumns: 3
            },
            dayGridMonth: {
                buttonText: '月間',
                dayMaxEvents: 3
            },
            timeGridWeek: {
                buttonText: '週間',
                slotEventOverlap: false
            },
            timeGridDay: {
                buttonText: '日別',
                slotEventOverlap: false
            }
        },
        // navLinkで日をクリックしたらその日の日別ビューへ
        navLinkDayClick: function(date) {
            calendar.changeView('timeGridDay', date);
            updateViewSwitcher('timeGridDay');
        },
        // イベントデータ取得
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
        // イベント表示カスタマイズ
        eventDidMount: function(info) {
            const props = info.event.extendedProps;
            if (props.type === 'reservation') {
                info.el.style.background = 'linear-gradient(135deg, #1a6b3c 0%, #0f4d2a 100%)';
                info.el.style.borderLeft = '3px solid #c8a84e';
            } else if (props.type === 'block') {
                info.el.style.background = 'linear-gradient(135deg, #e63946 0%, #c0392b 100%)';
                info.el.style.borderLeft = '3px solid #ff6b6b';
            }
        },
        // イベントクリックでモーダル表示
        eventClick: function(info) {
            const props = info.event.extendedProps;
            const header = document.getElementById('eventModalHeader');
            const title = document.getElementById('eventModalTitle');
            const body = document.getElementById('eventModalBody');

            if (props.type === 'reservation') {
                header.style.background = 'linear-gradient(135deg, #e8f5ee 0%, #d4edda 100%)';
                header.style.borderBottom = '2px solid #1a6b3c';
                title.innerHTML = '<i class="bi bi-calendar-check me-2" style="color:#1a6b3c"></i>予約情報';
                body.innerHTML = `
                    <table class="table table-borderless mb-0">
                        <tr><th style="width:35%;color:#4a4a6a">施設</th><td><strong>${props.facility}</strong></td></tr>
                        <tr><th style="color:#4a4a6a">団体</th><td>${props.organization}</td></tr>
                        <tr><th style="color:#4a4a6a">利用目的</th><td>${props.purpose || '未記入'}</td></tr>
                        <tr><th style="color:#4a4a6a">日時</th><td>${info.event.start ? formatDateTime(info.event.start, info.event.end) : '-'}</td></tr>
                    </table>
                `;
            } else if (props.type === 'block') {
                header.style.background = 'linear-gradient(135deg, #fde8e8 0%, #fadbd8 100%)';
                header.style.borderBottom = '2px solid #e63946';
                title.innerHTML = '<i class="bi bi-shield-lock me-2" style="color:#e63946"></i>学校行事';
                body.innerHTML = `
                    <table class="table table-borderless mb-0">
                        <tr><th style="width:35%;color:#4a4a6a">施設</th><td><strong>${props.facility}</strong></td></tr>
                        <tr><th style="color:#4a4a6a">理由</th><td>${props.reason}</td></tr>
                        <tr><th style="color:#4a4a6a">日時</th><td>${info.event.allDay ? '終日' : formatDateTime(info.event.start, info.event.end)}</td></tr>
                    </table>
                    <div class="alert alert-danger mt-3 mb-0" style="font-size:0.85rem">
                        <i class="bi bi-info-circle me-1"></i>この時間帯は学校行事のため予約できません。
                    </div>
                `;
            }
            eventModal.show();
        }
    });

    calendar.render();

    // --- 表示切替ボタン ---
    function updateViewSwitcher(viewName) {
        viewSwitcher.querySelectorAll('.btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === viewName);
        });
    }

    viewSwitcher.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const view = this.dataset.view;
            calendar.changeView(view);
            updateViewSwitcher(view);
        });
    });

    // --- 学校フィルター ---
    schoolSelect.addEventListener('change', function() {
        const schoolId = this.value;
        const options = facilitySelect.querySelectorAll('option');
        options.forEach(opt => {
            if (!opt.value) return;
            opt.style.display = (!schoolId || opt.dataset.school === schoolId) ? '' : 'none';
        });
        facilitySelect.value = '';
        calendar.refetchEvents();
    });

    facilitySelect.addEventListener('change', function() {
        calendar.refetchEvents();
    });

    // --- 日時フォーマット ---
    function formatDateTime(start, end) {
        if (!start) return '-';
        const dateStr = start.toLocaleDateString('ja-JP', {
            year: 'numeric', month: 'long', day: 'numeric', weekday: 'short'
        });
        const startTime = start.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
        if (!end) return dateStr + ' ' + startTime;
        const endTime = end.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
        return dateStr + ' ' + startTime + '〜' + endTime;
    }
});
