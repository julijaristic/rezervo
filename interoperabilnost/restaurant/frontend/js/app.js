(function () {
  var apiMeta = document.querySelector('meta[name="api-base"]');
  var API_BASE = (apiMeta && apiMeta.content) ? apiMeta.content.trim() : 'http://127.0.0.1:8001';
  var TOKEN_KEY = 'restaurant_auth_token';

  var authSection = document.getElementById('auth-section');
  var inboxSection = document.getElementById('inbox-section');
  var userInfo = document.getElementById('user-info');
  var usernameSpan = document.getElementById('username');
  var venueBadge = document.getElementById('venue-badge');
  var loginForm = document.getElementById('login-form');
  var registerForm = document.getElementById('register-form');
  var loginError = document.getElementById('login-error');
  var registerError = document.getElementById('register-error');
  var inboxList = document.getElementById('inbox-list');
  var inboxEmpty = document.getElementById('inbox-empty');
  var inboxVenueHint = document.getElementById('inbox-venue-hint');
  var btnRefreshInbox = document.getElementById('btn-refresh-inbox');
  var btnLogout = document.getElementById('btn-logout');
  var btnNotifications = document.getElementById('btn-notifications');
  var notifPanel = document.getElementById('notif-panel');
  var notificationsList = document.getElementById('notifications-list');
  var notificationsEmpty = document.getElementById('notifications-empty');
  var btnRefreshNotifications = document.getElementById('btn-refresh-notifications');
  var notifUnreadBadge = document.getElementById('notif-unread-badge');
  var toastRoot = document.getElementById('toast-root');

  var actionConfirmModal = document.getElementById('action-confirm-modal');
  var actionConfirmTitle = document.getElementById('action-confirm-title');
  var actionConfirmMessage = document.getElementById('action-confirm-message');
  var actionConfirmDetails = document.getElementById('action-confirm-details');
  var actionConfirmOk = document.getElementById('action-confirm-ok');
  var actionConfirmCancel = document.getElementById('action-confirm-cancel');
  var actionConfirmTableWrap = document.getElementById('action-confirm-table-wrap');
  var actionConfirmTable = document.getElementById('action-confirm-table');
  var actionConfirmTableLabel = document.getElementById('action-confirm-table-label');
  var actionConfirmReasonWrap = document.getElementById('action-confirm-reason-wrap');
  var actionConfirmReason = document.getElementById('action-confirm-reason');
  var inboxFilterDate = document.getElementById('inbox-filter-date');
  var inboxFilterStatus = document.getElementById('inbox-filter-status');
  var btnInboxFilter = document.getElementById('btn-inbox-filter');
  var btnInboxFilterClear = document.getElementById('btn-inbox-filter-clear');
  var inboxEmptyDefault = inboxEmpty ? inboxEmpty.textContent : '';
  var currentTableCount = 30;
  var resultPopup = document.getElementById('result-popup');
  var resultPopupBox = document.getElementById('result-popup-box');
  var resultPopupIcon = document.getElementById('result-popup-icon');
  var resultPopupTitle = document.getElementById('result-popup-title');
  var resultPopupLead = document.getElementById('result-popup-lead');
  var resultPopupClose = document.getElementById('result-popup-close');

  var pendingActionConfirm = null;
  var inboxRowsById = {};
  var inboxDetailModal = document.getElementById('inbox-detail-modal');
  var inboxDetailList = document.getElementById('inbox-detail-list');
  var inboxDetailClose = document.getElementById('inbox-detail-close');
  var pollInitialized = false;
  var lastInboxSignature = '';
  var lastMaxNotifId = 0;
  var POLL_MS = 2000;

  function token() {
    return sessionStorage.getItem(TOKEN_KEY);
  }

  function authHeaders() {
    var t = token();
    return t ? { Authorization: 'Bearer ' + t } : {};
  }

  function showToast(msg, type) {
    if (!toastRoot || !msg) return;
    var el = document.createElement('div');
    el.className = 'toast toast-' + (type || 'info');
    el.textContent = msg;
    toastRoot.appendChild(el);
    setTimeout(function () { el.remove(); }, 4000);
  }

  function cleanValidationMsg(msg) {
    var s = String(msg || '');
    if (s.indexOf('Value error, ') === 0) return s.slice('Value error, '.length);
    return s;
  }

  function formatApiError(err) {
    if (!err) return 'Greška';
    if (Array.isArray(err.detail)) {
      return err.detail.map(function (d) {
        var field = d.loc && d.loc.length ? d.loc[d.loc.length - 1] : '';
        return (field ? field + ': ' : '') + cleanValidationMsg(d.msg || String(d));
      }).join(' ');
    }
    if (typeof err.detail === 'string') return cleanValidationMsg(err.detail);
    return 'Greška';
  }

  function timeToMinutes(hhmm) {
    if (!hhmm) return 0;
    var p = hhmm.split(':');
    return parseInt(p[0], 10) * 60 + parseInt(p[1], 10);
  }

  function validateOpeningHours() {
    var wdOpen = document.getElementById('nv-wd-open').value || '10:00';
    var wdClose = document.getElementById('nv-wd-close').value || '22:00';
    var weOpen = document.getElementById('nv-we-open').value || '10:00';
    var weClose = document.getElementById('nv-we-close').value || '22:00';
    if (timeToMinutes(wdClose) <= timeToMinutes(wdOpen)) {
      return 'Pon-Pet: kraj radnog vremena mora biti posle početka (npr. 10:00-22:00). Rad posle ponoći trenutno nije podržan.';
    }
    if (timeToMinutes(weClose) <= timeToMinutes(weOpen)) {
      return 'Vikend: kraj radnog vremena mora biti posle početka (npr. 10:00-22:00). Rad posle ponoći trenutno nije podržan.';
    }
    return null;
  }

  function inboxQueryString() {
    if (inboxFilterDate && inboxFilterDate.value) {
      return '?date=' + encodeURIComponent(inboxFilterDate.value);
    }
    return '';
  }

  function formatFilterDate(iso) {
    var parts = String(iso || '').split('-');
    if (parts.length !== 3) return iso;
    return parts[2] + '. ' + parts[1] + '. ' + parts[0] + '.';
  }

  function updateFilterStatus(count) {
    if (!inboxFilterStatus) return;
    var iso = inboxFilterDate && inboxFilterDate.value;
    if (!iso) {
      inboxFilterStatus.textContent = '';
      inboxFilterStatus.classList.add('hidden');
      return;
    }
    var label = formatFilterDate(iso);
    inboxFilterStatus.textContent = count
      ? count + ' ' + (count % 10 === 1 && count % 100 !== 11 ? 'zahtev' : 'zahteva') + ' za ' + label
      : 'Nema zahteva za ' + label;
    inboxFilterStatus.classList.remove('hidden');
  }

  function staffNotifTitle(kind) {
    if (kind === 'reservation_created') return 'Novi zahtev';
    if (kind === 'reservation_updated') return 'Izmena zahteva';
    if (kind === 'reservation_cancelled') return 'Otkaz';
    if (kind === 'webhook_ok') return 'Odluka poslata';
    if (kind === 'webhook_error') return 'Greška slanja';
    return 'Obaveštenje';
  }

  function fillDetailsList(dl, rows) {
    if (!dl) return;
    dl.innerHTML = '';
    (rows || []).forEach(function (row) {
      if (!row || !row.value) return;
      var dt = document.createElement('dt');
      dt.textContent = row.label;
      var dd = document.createElement('dd');
      dd.textContent = row.value;
      dl.appendChild(dt);
      dl.appendChild(dd);
    });
  }

  function decisionLabel(decision) {
    if (decision === 'new') return 'Na čekanju - niste odgovorili';
    if (decision === 'sent_confirmed') return 'Odobreno i poslato gostu';
    if (decision === 'sent_rejected') return 'Odbijeno i poslato gostu';
    return decision || '-';
  }

  function rezervoStatusLabel(status) {
    if (status === 'pending') return 'Na čekanju';
    if (status === 'confirmed') return 'Potvrđeno';
    if (status === 'rejected') return 'Odbijeno';
    if (status === 'cancelled') return 'Otkazano';
    return status || '-';
  }

  function formatGuestLine(row) {
    var name = (row.guest_name || '').trim();
    var phone = (row.guest_phone || '').trim();
    if (name && phone) return name + ' · ' + phone;
    if (name) return name;
    if (phone) return phone;
    return '';
  }

  function formatTableLine(row) {
    if (row.table_number != null && row.table_number !== '') {
      return 'Sto ' + row.table_number;
    }
    return '';
  }

  function inboxDetailRows(row) {
    var rows = [
      { label: 'Ime gosta', value: (row.guest_name && row.guest_name.trim()) || '-' },
      { label: 'Telefon', value: (row.guest_phone && row.guest_phone.trim()) || '-' },
      { label: 'Broj rezervacije', value: '#' + row.rezervo_reservation_id },
      { label: 'Termin', value: row.slot_date + ', ' + row.start_time + '–' + row.end_time },
      { label: 'Broj gostiju', value: String(row.guest_count) },
      {
        label: 'Sto',
        value: row.table_number != null && row.table_number !== '' ? String(row.table_number) : '-',
      },
      { label: 'Status rezervacije', value: rezervoStatusLabel(row.rezervo_status) },
      { label: 'Vaša odluka', value: decisionLabel(row.decision_status) },
    ];
    if (row.rejection_reason && row.rejection_reason.trim()) {
      rows.push({ label: 'Razlog odbijanja', value: row.rejection_reason.trim() });
    }
    return rows;
  }

  function openInboxDetail(inboxId) {
    var row = inboxRowsById[inboxId];
    if (!row || !inboxDetailModal) return;
    fillDetailsList(inboxDetailList, inboxDetailRows(row));
    inboxDetailModal.classList.remove('hidden');
  }

  function closeInboxDetail() {
    if (inboxDetailModal) inboxDetailModal.classList.add('hidden');
  }

  function closeActionConfirmModal() {
    if (actionConfirmModal) actionConfirmModal.classList.add('hidden');
    pendingActionConfirm = null;
    if (actionConfirmTableWrap) actionConfirmTableWrap.classList.add('hidden');
    if (actionConfirmReasonWrap) actionConfirmReasonWrap.classList.add('hidden');
    if (actionConfirmReason) actionConfirmReason.value = '';
    if (actionConfirmOk) {
      actionConfirmOk.disabled = false;
      actionConfirmOk.textContent = 'Potvrdi';
      actionConfirmOk.className = 'btn btn-primary';
    }
  }

  function openActionConfirm(options) {
    pendingActionConfirm = options;
    if (actionConfirmTableWrap) {
      actionConfirmTableWrap.classList.toggle('hidden', !options.showTableInput);
    }
    if (actionConfirmReasonWrap) {
      actionConfirmReasonWrap.classList.toggle('hidden', !options.showRejectReason);
    }
    if (options.showTableInput && actionConfirmTable) {
      actionConfirmTable.value = options.defaultTable != null ? String(options.defaultTable) : '';
      actionConfirmTable.max = String(currentTableCount);
      actionConfirmTable.min = '1';
      if (actionConfirmTableLabel) {
        actionConfirmTableLabel.textContent = 'Broj stola (1-' + currentTableCount + ')';
      }
    }
    if (actionConfirmTitle) actionConfirmTitle.textContent = options.title || 'Potvrda';
    if (actionConfirmMessage) {
      actionConfirmMessage.textContent = options.message || '';
      actionConfirmMessage.classList.toggle('hidden', !options.message);
    }
    fillDetailsList(actionConfirmDetails, options.details || []);
    if (actionConfirmOk) {
      actionConfirmOk.textContent = options.confirmLabel || 'Potvrdi';
      actionConfirmOk.className = 'btn ' + (options.confirmClass || 'btn-primary');
    }
    if (actionConfirmModal) actionConfirmModal.classList.remove('hidden');
  }

  function showResult(kind, title, lead) {
    if (!resultPopup || !resultPopupBox) return;
    resultPopupBox.className = 'popup-box status-result';
    if (kind === 'confirmed') resultPopupBox.classList.add('confirmed');
    else if (kind === 'rejected') resultPopupBox.classList.add('rejected');
    else resultPopupBox.classList.add('owner-alert');
    if (resultPopupIcon) {
      resultPopupIcon.textContent = kind === 'rejected' ? 'X' : 'OK';
    }
    if (resultPopupTitle) resultPopupTitle.textContent = title;
    if (resultPopupLead) {
      resultPopupLead.textContent = lead || '';
      resultPopupLead.classList.toggle('hidden', !lead);
    }
    resultPopup.classList.remove('hidden');
  }

  function closeResultPopup() {
    if (resultPopup) resultPopup.classList.add('hidden');
  }

  function api(path, options) {
    options = options || {};
    var headers = Object.assign({ 'Content-Type': 'application/json' }, authHeaders(), options.headers || {});
    return fetch(API_BASE + path, Object.assign({}, options, { headers: headers }))
      .then(function (r) {
        return r.json().then(function (body) {
          if (!r.ok) throw body;
          return body;
        });
      });
  }

  function showLoggedIn(me) {
    authSection.classList.add('hidden');
    inboxSection.classList.remove('hidden');
    userInfo.classList.remove('hidden');
    usernameSpan.textContent = me.username || '';
    if (venueBadge) {
      venueBadge.textContent = me.venue_name || ('Lokal #' + me.venue_id);
      venueBadge.classList.remove('hidden');
    }
    currentTableCount = me.table_count && me.table_count > 0 ? me.table_count : 30;
    if (inboxVenueHint) {
      inboxVenueHint.textContent = (me.venue_name || me.venue_id) + ' · ' + currentTableCount + ' stolova';
    }
    pollInitialized = false;
    lastInboxSignature = '';
    lastMaxNotifId = 0;
    refreshDashboard(false).then(function () {
      pollInitialized = true;
    });
  }

  function refreshDashboard(notify) {
    return Promise.all([loadInbox(notify), loadNotifications(notify)]);
  }

  function logout() {
    sessionStorage.removeItem(TOKEN_KEY);
    userInfo.classList.add('hidden');
    if (venueBadge) venueBadge.classList.add('hidden');
    inboxSection.classList.add('hidden');
    authSection.classList.remove('hidden');
  }

  function statusBadge(decision) {
    if (decision === 'new') return '<span class="badge badge-pending">Na čekanju</span>';
    if (decision === 'sent_confirmed') return '<span class="badge badge-success">Poslato: potvrđeno</span>';
    if (decision === 'sent_rejected') return '<span class="badge badge-danger">Poslato: odbijeno</span>';
    return decision;
  }

  function inboxSignature(items) {
    return (items || [])
      .map(function (r) {
        return [
          r.id,
          r.rezervo_status,
          r.decision_status,
          r.table_number != null ? r.table_number : '',
          r.guest_name || '',
          r.guest_phone || '',
        ].join(':');
      })
      .join('|');
  }

  function loadInbox(notify) {
    return api('/inbox/' + inboxQueryString())
      .then(function (items) {
        var sig = inboxSignature(items);
        if (notify && pollInitialized && lastInboxSignature && sig !== lastInboxSignature) {
          showToast('Inbox je ažuriran (novi zahtev, otkaz ili promena).', 'info');
        }
        lastInboxSignature = sig;

        inboxList.innerHTML = '';
        inboxRowsById = {};
        var activeDate = inboxFilterDate && inboxFilterDate.value;
        updateFilterStatus(items.length);
        if (!items.length) {
          inboxEmpty.textContent = activeDate
            ? 'Nema zahteva za izabrani datum.'
            : inboxEmptyDefault;
          inboxEmpty.classList.remove('hidden');
          return;
        }
        inboxEmpty.textContent = inboxEmptyDefault;
        inboxEmpty.classList.add('hidden');
        items.forEach(function (row) {
          inboxRowsById[row.id] = row;
          var li = document.createElement('li');
          li.className = 'reservation-item card reservation-item-clickable';
          li.setAttribute('data-inbox-id', String(row.id));
          li.setAttribute('role', 'button');
          li.setAttribute('tabindex', '0');
          li.setAttribute('aria-label', 'Detalji rezervacije #' + row.rezervo_reservation_id);
          var guestLine = formatGuestLine(row);
          var tableLine = formatTableLine(row);
          var actions = '';
          if (row.decision_status === 'new') {
            actions =
              '<button type="button" class="btn btn-success btn-sm" data-approve="' + row.id + '">Odobri</button> ' +
              '<button type="button" class="btn btn-danger btn-sm" data-reject="' + row.id + '">Odbij</button>';
          } else {
            actions = '<span class="muted hint-detail">Kliknite za detalje</span>';
          }
          li.innerHTML =
            '<div class="reservation-item-main">' +
            '<strong>#' + row.rezervo_reservation_id + '</strong> ' + statusBadge(row.decision_status) +
            '<p class="muted guest-line">' + (guestLine || 'Gost - podaci stižu sa novim zahtevom') + '</p>' +
            '<p class="muted">' + row.slot_date + ' ' + row.start_time + '–' + row.end_time +
            ' · ' + row.guest_count + ' gostiju · ' + rezervoStatusLabel(row.rezervo_status) +
            (tableLine ? ' · ' + tableLine : '') +
            '</p>' +
            '</div><div class="reservation-item-actions">' + actions + '</div>';
          inboxList.appendChild(li);
        });
        inboxList.querySelectorAll('[data-approve]').forEach(function (btn) {
          btn.addEventListener('click', function (e) {
            e.stopPropagation();
            openDecideConfirm(btn.getAttribute('data-approve'), 'approve');
          });
        });
        inboxList.querySelectorAll('[data-reject]').forEach(function (btn) {
          btn.addEventListener('click', function (e) {
            e.stopPropagation();
            openDecideConfirm(btn.getAttribute('data-reject'), 'reject');
          });
        });
        inboxList.querySelectorAll('.reservation-item-clickable').forEach(function (li) {
          li.addEventListener('click', function () {
            openInboxDetail(li.getAttribute('data-inbox-id'));
          });
          li.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              openInboxDetail(li.getAttribute('data-inbox-id'));
            }
          });
        });
      })
      .catch(function (err) {
        if (err && (err.detail === 'Neispravan token' || err.detail === 'Nije prosleđen token')) logout();
        showToast(formatApiError(err), 'error');
      });
  }

  function openDecideConfirm(inboxId, action) {
    var row = inboxRowsById[inboxId];
    if (!row) return;
    var isApprove = action === 'approve';
    openActionConfirm({
      title: isApprove ? 'Odobriti rezervaciju?' : 'Odbiti rezervaciju?',
      message: isApprove
        ? 'Unesite broj stola koji dodeljujete gostu.'
        : 'Gost će biti obavešten da termin nije prihvaćen.',
      details: inboxDetailRows(row),
      confirmLabel: isApprove ? 'Odobri' : 'Odbij',
      confirmClass: isApprove ? 'btn-success' : 'btn-danger',
      showTableInput: isApprove,
      showRejectReason: !isApprove,
      onConfirm: function () {
        var apiOptions = { method: 'POST' };
        if (isApprove) {
          var tableNum = actionConfirmTable ? parseInt(actionConfirmTable.value, 10) : NaN;
          if (!tableNum || tableNum < 1 || tableNum > currentTableCount) {
            showToast('Unesite broj stola od 1 do ' + currentTableCount + '.', 'error');
            return Promise.reject(new Error('validation'));
          }
          apiOptions.body = JSON.stringify({ table_number: tableNum });
        } else {
          var reason = actionConfirmReason ? actionConfirmReason.value.trim() : '';
          apiOptions.body = JSON.stringify(reason ? { reason: reason } : {});
        }
        return api('/inbox/' + inboxId + '/' + action, apiOptions)
          .then(function () {
            closeActionConfirmModal();
            showResult(
              isApprove ? 'confirmed' : 'rejected',
              isApprove ? 'Rezervacija potvrđena' : 'Rezervacija odbijena',
              isApprove
                ? 'Gost je obavešten o potvrdi termina.'
                : 'Gost je obavešten da termin nije prihvaćen.'
            );
            refreshDashboard(false);
          });
      },
    });
  }

  function loadNotifications(notify) {
    return api('/notifications/')
      .then(function (items) {
        var maxNotifId = 0;
        items.forEach(function (n) {
          if (n.id > maxNotifId) maxNotifId = n.id;
        });
        if (notify && pollInitialized && maxNotifId > lastMaxNotifId) {
          var latest = items.reduce(function (best, n) {
            return !best || n.id > best.id ? n : best;
          }, null);
          var msg = latest && latest.message ? latest.message : 'Imate novo obaveštenje.';
          showToast(msg, 'info');
          if (notifPanel && notifPanel.classList.contains('hidden')) {
            notifUnreadBadge.classList.remove('hidden');
          }
        }
        lastMaxNotifId = maxNotifId;
        var unread = items.filter(function (n) { return !n.read; }).length;
        if (unread > 0) {
          notifUnreadBadge.textContent = String(unread);
          notifUnreadBadge.classList.remove('hidden');
        } else {
          notifUnreadBadge.classList.add('hidden');
        }
        notificationsList.innerHTML = '';
        if (!items.length) {
          notificationsEmpty.classList.remove('hidden');
          return;
        }
        notificationsEmpty.classList.add('hidden');
        items.forEach(function (n) {
          var li = document.createElement('li');
          li.className = 'notif-item kind-' + (n.kind || '') + (n.read ? ' read' : ' unread');
          var title = document.createElement('strong');
          title.textContent = staffNotifTitle(n.kind);
          var body = document.createElement('span');
          body.className = 'notif-item-body';
          body.textContent = n.message || '';
          li.appendChild(title);
          li.appendChild(body);
          li.addEventListener('click', function () {
            if (!n.read) {
              api('/notifications/' + n.id + '/read', { method: 'PATCH' }).then(loadNotifications);
            }
          });
          notificationsList.appendChild(li);
        });
      })
      .catch(function (err) {
        if (err && (err.detail === 'Neispravan token' || err.detail === 'Nije prosleđen token')) logout();
      });
  }

  document.querySelectorAll('.tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      var t = this.getAttribute('data-tab');
      document.querySelectorAll('.tab').forEach(function (x) { x.classList.remove('active'); });
      document.querySelector('.tab[data-tab="' + t + '"]').classList.add('active');
      loginForm.classList.toggle('hidden', t !== 'login');
      registerForm.classList.toggle('hidden', t !== 'register');
      loginError.classList.add('hidden');
      if (registerError) registerError.classList.add('hidden');
    });
  });

  loginForm.addEventListener('submit', function (e) {
    e.preventDefault();
    loginError.classList.add('hidden');
    var username = document.getElementById('login-username').value.trim();
    var password = document.getElementById('login-password').value;
    fetch(API_BASE + '/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username, password: password }),
    })
      .then(function (r) { return r.json().then(function (b) { if (!r.ok) throw b; return b; }); })
      .then(function (data) {
        sessionStorage.setItem(TOKEN_KEY, data.access_token);
        return api('/auth/me');
      })
      .then(showLoggedIn)
      .catch(function (err) {
        loginError.textContent = formatApiError(err);
        loginError.classList.remove('hidden');
      });
  });

  if (registerForm) {
    registerForm.addEventListener('submit', function (e) {
      e.preventDefault();
      registerError.classList.add('hidden');
      var hoursErr = validateOpeningHours();
      if (hoursErr) {
        registerError.textContent = hoursErr;
        registerError.classList.remove('hidden');
        return;
      }
      var submitBtn = registerForm.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Registracija…';
      }
      var payload = {
        username: document.getElementById('reg-username').value.trim(),
        password: document.getElementById('reg-password').value,
        new_venue: {
          name: document.getElementById('nv-name').value.trim(),
          address: document.getElementById('nv-address').value.trim(),
          city: document.getElementById('nv-city').value.trim(),
          country: document.getElementById('nv-country').value.trim() || 'Srbija',
          phone: document.getElementById('nv-phone').value.trim(),
          email: document.getElementById('nv-email').value.trim(),
          weekday_open: document.getElementById('nv-wd-open').value || '10:00',
          weekday_close: document.getElementById('nv-wd-close').value || '22:00',
          weekend_open: document.getElementById('nv-we-open').value || '10:00',
          weekend_close: document.getElementById('nv-we-close').value || '22:00',
          table_count: parseInt(document.getElementById('nv-table-count').value, 10) || 30,
        },
      };
      fetch(API_BASE + '/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
        .then(function (r) { return r.json().then(function (b) { if (!r.ok) throw b; return b; }); })
        .then(function (data) {
          sessionStorage.setItem(TOKEN_KEY, data.access_token);
          return api('/auth/me');
        })
        .then(function (me) {
          showToast('Nalog i lokal su kreirani.', 'success');
          showLoggedIn(me);
        })
        .catch(function (err) {
          registerError.textContent = formatApiError(err);
          registerError.classList.remove('hidden');
        })
        .finally(function () {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Registruj nalog';
          }
        });
    });
  }

  btnLogout.addEventListener('click', logout);
  btnRefreshInbox.addEventListener('click', function () { refreshDashboard(false); });
  if (btnInboxFilter) {
    btnInboxFilter.addEventListener('click', function () { loadInbox(false); });
  }
  if (inboxFilterDate) {
    inboxFilterDate.addEventListener('change', function () { loadInbox(false); });
  }
  if (btnInboxFilterClear) {
    btnInboxFilterClear.addEventListener('click', function () {
      if (inboxFilterDate) inboxFilterDate.value = '';
      loadInbox(false);
    });
  }
  btnRefreshNotifications.addEventListener('click', function () { loadNotifications(false); });
  btnNotifications.addEventListener('click', function () {
    notifPanel.classList.toggle('hidden');
    loadNotifications(false);
  });
  if (inboxDetailClose) inboxDetailClose.addEventListener('click', closeInboxDetail);
  if (inboxDetailModal) {
    inboxDetailModal.addEventListener('click', function (e) {
      if (e.target === inboxDetailModal) closeInboxDetail();
    });
  }

  if (actionConfirmCancel) actionConfirmCancel.addEventListener('click', closeActionConfirmModal);
  if (actionConfirmModal) {
    actionConfirmModal.addEventListener('click', function (e) {
      if (e.target === actionConfirmModal) closeActionConfirmModal();
    });
  }
  if (actionConfirmOk) {
    actionConfirmOk.addEventListener('click', function () {
      if (!pendingActionConfirm || !pendingActionConfirm.onConfirm) return;
      actionConfirmOk.disabled = true;
      actionConfirmOk.textContent = 'Slanje…';
      Promise.resolve(pendingActionConfirm.onConfirm())
        .catch(function (err) {
          if (err && err.message === 'validation') return;
          showToast(formatApiError(err), 'error');
          actionConfirmOk.disabled = false;
          actionConfirmOk.textContent = pendingActionConfirm.confirmLabel || 'Potvrdi';
        });
    });
  }
  if (resultPopupClose) resultPopupClose.addEventListener('click', closeResultPopup);
  if (resultPopup) {
    resultPopup.addEventListener('click', function (e) {
      if (e.target === resultPopup) closeResultPopup();
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      closeActionConfirmModal();
      closeResultPopup();
      closeInboxDetail();
    }
  });

  if (token()) {
    api('/auth/me')
      .then(showLoggedIn)
      .catch(logout);
  }

  setInterval(function () {
    if (token() && document.visibilityState === 'visible') {
      refreshDashboard(true);
    }
  }, POLL_MS);

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible' && token()) {
      refreshDashboard(true);
    }
  });
})();
