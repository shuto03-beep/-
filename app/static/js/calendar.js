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
        dayMaxEvents: false,
        expandRows: true,
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
                multiMonthMaxColumns: 3,
                dayMaxEvents: 2,
                moreLinkText: function(num) { return '+' + num; }
            },
            dayGridMonth: {
                dayMaxEvents: 4,
                moreLinkText: function(num) { return '他' + num + '件'; }
            },
            timeGridWeek: {
                slotEventOverlap: false
            },
            timeGridDay: {
                slotEventOverlap: false
            }
        },
        // 日クリックで日別ビューへ
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
                .then(r => r.json())
                .then(data => successCallback(data))
                .catch(err => failureCallback(err));
        },

        // ========================================
        // ビュー別イベント表示カスタマイズ
        // ========================================
        eventContent: function(arg) {
            const viewType = arg.view.type;
            const props = arg.event.extendedProps;

            // --- 年間ビュー: コンパクトなドット+短い名前 ---
            if (viewType === 'multiMonthYear') {
                return renderYearView(arg, props);
            }
            // --- 月間ビュー: 施設名+団体名を一覧性高く ---
            if (viewType === 'dayGridMonth') {
                return renderMonthView(arg, props);
            }
            // --- 週間・日別ビュー: 詳細情報を表示 ---
            if (viewType === 'timeGridWeek' || viewType === 'timeGridDay') {
                return renderWeekDayView(arg, props, viewType);
            }

            // フォールバック
            return { html: '<span>' + arg.event.title + '</span>' };
        },

        // イベント装飾
        eventDidMount: function(info) {
            const props = info.event.extendedProps;
            const viewType = info.view.type;

            if (props.type === 'block') {
                // ブロックは常に赤系統
                info.el.style.background = 'repeating-linear-gradient(45deg, #c0392b, #c0392b 4px, #e74c3c 4px, #e74c3c 8px)';
                info.el.style.borderLeft = '4px solid #922b21';
                info.el.style.color = '#fff';
                info.el.classList.add('event-block');
            } else if (props.type === 'reservation') {
                info.el.style.borderLeft = '4px solid ' + (info.event.borderColor || '#0f4d2a');
                info.el.classList.add('event-reservation');

                // 認定団体マーク
                if (props.isCertified && (viewType === 'timeGridWeek' || viewType === 'timeGridDay')) {
                    info.el.classList.add('event-certified');
                }
            }

            // ツールチップ（全ビュー共通）
            if (props.type === 'reservation') {
                info.el.title = props.school + ' ' + props.facility + '\n'
                    + props.organization + (props.isCertified ? ' ★認定' : '') + '\n'
                    + props.timeRange + '\n'
                    + (props.purpose ? '目的: ' + props.purpose : '');
            } else {
                info.el.title = '【学校行事】' + props.reason + '\n' + props.facility;
            }
        },

        // イベントクリックでモーダル表示
        eventClick: function(info) {
            showEventModal(info);
        }
    });

    calendar.render();

    // ==========================================
    // ビュー別レンダリング関数
    // ==========================================

    // --- 年間ビュー ---
    // コンパクト: 施設の色ドット + 団体の頭文字
    function renderYearView(arg, props) {
        if (props.type === 'block') {
            return {
                html: '<div class="year-event year-block">'
                    + '<i class="bi bi-x-circle-fill"></i> '
                    + escapeHtml(truncate(props.reason, 6))
                    + '</div>'
            };
        }
        return {
            html: '<div class="year-event year-reservation">'
                + '<span class="facility-dot" style="background:' + arg.event.backgroundColor + '"></span>'
                + escapeHtml(truncate(props.organization, 5))
                + '</div>'
        };
    }

    // --- 月間ビュー ---
    // 施設名 + 団体名 + 認定マーク
    function renderMonthView(arg, props) {
        if (props.type === 'block') {
            return {
                html: '<div class="month-event month-block">'
                    + '<i class="bi bi-shield-lock-fill me-1"></i>'
                    + '<span class="month-block-reason">' + escapeHtml(truncate(props.reason, 10)) + '</span>'
                    + '</div>'
            };
        }
        var certBadge = props.isCertified
            ? '<span class="cert-mark" title="いなチャレ認定">★</span>'
            : '';
        return {
            html: '<div class="month-event month-reservation">'
                + '<span class="month-facility">' + escapeHtml(props.facility) + '</span>'
                + '<span class="month-org">' + certBadge + escapeHtml(truncate(props.organization, 8)) + '</span>'
                + '<span class="month-time">' + props.timeRange + '</span>'
                + '</div>'
        };
    }

    // --- 週間・日別ビュー ---
    // 団体名 + 施設名 + 目的 + 参加人数
    function renderWeekDayView(arg, props, viewType) {
        if (props.type === 'block') {
            return {
                html: '<div class="week-event week-block">'
                    + '<div class="week-block-label"><i class="bi bi-shield-lock-fill me-1"></i>学校行事</div>'
                    + '<div class="week-block-reason">' + escapeHtml(props.reason) + '</div>'
                    + '<div class="week-block-facility">' + escapeHtml(props.facility) + '</div>'
                    + '</div>'
            };
        }

        var certBadge = props.isCertified
            ? '<span class="week-cert-badge">認定</span>'
            : '';
        var participantsHtml = props.participants > 0
            ? '<span class="week-participants"><i class="bi bi-people-fill"></i>' + props.participants + '名</span>'
            : '';
        var purposeHtml = props.purpose
            ? '<div class="week-purpose">' + escapeHtml(truncate(props.purpose, viewType === 'timeGridDay' ? 20 : 12)) + '</div>'
            : '';

        return {
            html: '<div class="week-event week-reservation">'
                + '<div class="week-org-line">'
                + '<span class="week-org-name">' + escapeHtml(props.organization) + '</span>'
                + certBadge
                + '</div>'
                + '<div class="week-facility-line">'
                + '<i class="bi bi-geo-alt-fill me-1"></i>'
                + escapeHtml(props.facility)
                + ' <span class="week-school-tag">' + escapeHtml(getSchoolShort(props.school)) + '</span>'
                + '</div>'
                + purposeHtml
                + '<div class="week-meta">'
                + participantsHtml
                + '</div>'
                + '</div>'
        };
    }

    // ==========================================
    // モーダル表示
    // ==========================================
    function showEventModal(info) {
        const props = info.event.extendedProps;
        const header = document.getElementById('eventModalHeader');
        const title = document.getElementById('eventModalTitle');
        const body = document.getElementById('eventModalBody');

        if (props.type === 'reservation') {
            var certHtml = props.isCertified
                ? '<span class="badge badge-certified ms-2"><i class="bi bi-award me-1"></i>いなチャレ認定</span>'
                : '<span class="badge badge-general ms-2">一般団体</span>';

            header.className = 'modal-header modal-header-reservation';
            title.innerHTML = '<i class="bi bi-calendar-check me-2"></i>予約情報';
            body.innerHTML =
                '<div class="modal-org-name">' + escapeHtml(props.organization) + certHtml + '</div>'
                + '<table class="table table-borderless modal-detail-table">'
                + '<tr><td class="modal-label"><i class="bi bi-building"></i>学校</td><td>' + escapeHtml(props.school) + '</td></tr>'
                + '<tr><td class="modal-label"><i class="bi bi-door-open"></i>施設</td><td><strong>' + escapeHtml(props.facility) + '</strong> <span class="badge badge-general">' + escapeHtml(props.facilityType) + '</span></td></tr>'
                + '<tr><td class="modal-label"><i class="bi bi-clock"></i>日時</td><td>' + formatDateTime(info.event.start, info.event.end) + '</td></tr>'
                + '<tr><td class="modal-label"><i class="bi bi-chat-text"></i>目的</td><td>' + escapeHtml(props.purpose || '未記入') + '</td></tr>'
                + (props.participants > 0
                    ? '<tr><td class="modal-label"><i class="bi bi-people"></i>参加人数</td><td>' + props.participants + '名</td></tr>'
                    : '')
                + '</table>';
        } else {
            header.className = 'modal-header modal-header-block';
            title.innerHTML = '<i class="bi bi-shield-lock me-2"></i>学校行事ブロック';
            body.innerHTML =
                '<div class="modal-block-alert">'
                + '<i class="bi bi-exclamation-triangle me-2"></i>この時間帯は学校行事のため予約できません'
                + '</div>'
                + '<table class="table table-borderless modal-detail-table">'
                + '<tr><td class="modal-label"><i class="bi bi-building"></i>学校</td><td>' + escapeHtml(props.school) + '</td></tr>'
                + '<tr><td class="modal-label"><i class="bi bi-door-open"></i>対象施設</td><td><strong>' + escapeHtml(props.facility) + '</strong></td></tr>'
                + '<tr><td class="modal-label"><i class="bi bi-megaphone"></i>理由</td><td>' + escapeHtml(props.reason) + '</td></tr>'
                + '<tr><td class="modal-label"><i class="bi bi-clock"></i>日時</td><td>' + (info.event.allDay ? '終日' : formatDateTime(info.event.start, info.event.end)) + '</td></tr>'
                + '</table>';
        }
        eventModal.show();
    }

    // ==========================================
    // 表示切替ボタン
    // ==========================================
    function updateViewSwitcher(viewName) {
        viewSwitcher.querySelectorAll('.btn').forEach(function(btn) {
            btn.classList.toggle('active', btn.dataset.view === viewName);
        });
    }

    viewSwitcher.querySelectorAll('.btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var view = this.dataset.view;
            calendar.changeView(view);
            updateViewSwitcher(view);
        });
    });

    // ==========================================
    // フィルター
    // ==========================================
    schoolSelect.addEventListener('change', function() {
        var schoolId = this.value;
        facilitySelect.querySelectorAll('option').forEach(function(opt) {
            if (!opt.value) return;
            opt.style.display = (!schoolId || opt.dataset.school === schoolId) ? '' : 'none';
        });
        facilitySelect.value = '';
        calendar.refetchEvents();
    });

    facilitySelect.addEventListener('change', function() {
        calendar.refetchEvents();
    });

    // ==========================================
    // ヘルパー関数
    // ==========================================
    function truncate(str, len) {
        if (!str) return '';
        return str.length > len ? str.substring(0, len) + '…' : str;
    }

    function escapeHtml(str) {
        if (!str) return '';
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function getSchoolShort(name) {
        if (name.indexOf('北') >= 0) return '北中';
        return '稲中';
    }

    function formatDateTime(start, end) {
        if (!start) return '-';
        var dateStr = start.toLocaleDateString('ja-JP', {
            year: 'numeric', month: 'long', day: 'numeric', weekday: 'short'
        });
        var startTime = start.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
        if (!end) return dateStr + ' ' + startTime;
        var endTime = end.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
        return dateStr + ' ' + startTime + '〜' + endTime;
    }
});
