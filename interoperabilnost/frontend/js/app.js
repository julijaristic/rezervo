(function () {
  const apiMeta = document.querySelector('meta[name="api-base"]');
  const API_BASE = (apiMeta && apiMeta.content) ? apiMeta.content.trim() : 'http://127.0.0.1:8000';
  const TOKEN_KEY = 'auth_token';
  const NOTIFICATION_POPUP_KEY = 'notification_popup_shown';
  const POLL_RESERVATION_KEY = 'poll_reservation_id';

  const authSection = document.getElementById('auth-section');
  const reservationSection = document.getElementById('reservation-section');
  const userInfo = document.getElementById('user-info');
  const userRole = document.getElementById('user-role');
  const usernameSpan = document.getElementById('username');
  const btnLogout = document.getElementById('btn-logout');
  const btnNotifications = document.getElementById('btn-notifications');
  const notifPanel = document.getElementById('notif-panel');

  const loginForm = document.getElementById('login-form');
  const loginUsername = document.getElementById('login-username');
  const loginPassword = document.getElementById('login-password');
  const loginError = document.getElementById('login-error');

  const registerForm = document.getElementById('register-form');
  const registerError = document.getElementById('register-error');
  const registerSuccess = document.getElementById('register-success');

  const reservationForm = document.getElementById('reservation-form');
  const btnSubmitReservation = document.getElementById('btn-submit-reservation');
  const resVenue = document.getElementById('res-venue');
  const resDate = document.getElementById('res-date');
  const resStart = document.getElementById('res-start');
  const DEFAULT_STAY_HOURS = 2;
  const resGuests = document.getElementById('res-guests');
  const resNotes = document.getElementById('res-notes');
  const reservationError = document.getElementById('reservation-error');
  const reservationSuccess = document.getElementById('reservation-success');
  const venueCards = document.getElementById('venue-cards');
  const venueCardsEmpty = document.getElementById('venue-cards-empty');
  const venueHint = document.getElementById('venue-hint');
  const btnRefreshVenues = document.getElementById('btn-refresh-venues');
  const pendingReservationBanner = document.getElementById('pending-reservation-banner');

  const myReservationsList = document.getElementById('my-reservations-list');
  const myReservationsEmpty = document.getElementById('my-reservations-empty');
  const btnRefreshReservations = document.getElementById('btn-refresh-reservations');

  const notificationsList = document.getElementById('notifications-list');
  const notificationsEmpty = document.getElementById('notifications-empty');
  const btnRefreshNotifications = document.getElementById('btn-refresh-notifications');
  const notifUnreadBadge = document.getElementById('notif-unread-badge');

  const confirmedPopup = document.getElementById('confirmed-popup');
  const confirmedPopupBox = document.getElementById('confirmed-popup-box');
  const confirmedPopupTitle = document.getElementById('confirmed-popup-title');
  const confirmedPopupIcon = document.getElementById('confirmed-popup-icon');
  const confirmedPopupLead = document.getElementById('confirmed-popup-lead');
  const confirmedPopupDetails = document.getElementById('confirmed-popup-details');
  const confirmedPopupClose = document.getElementById('confirmed-popup-close');
  const actionConfirmModal = document.getElementById('action-confirm-modal');
  const actionConfirmTitle = document.getElementById('action-confirm-title');
  const actionConfirmMessage = document.getElementById('action-confirm-message');
  const actionConfirmDetails = document.getElementById('action-confirm-details');
  const actionConfirmOk = document.getElementById('action-confirm-ok');
  const actionConfirmCancel = document.getElementById('action-confirm-cancel');
  const toastRoot = document.getElementById('toast-root');

  var pendingActionConfirm = null;
  var cachedVenues = [];
  var pollIntervalId = null;

  var editResModal = document.getElementById('edit-reservation-modal');
  var editResForm = document.getElementById('edit-reservation-form');

  function formInput(id) {
    return document.getElementById(id);
  }

  function inputValue(id, fallback) {
    var el = formInput(id);
    if (!el || el.value == null || el.value === '') return fallback != null ? fallback : '';
    return el.value;
  }

  function todayIso() {
    var d = new Date();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return d.getFullYear() + '-' + m + '-' + day;
  }

  function setMinReservationDate() {
    if (resDate) resDate.min = todayIso();
  }

  function formatApiError(err) {
    if (!err) return 'Greška';
    if (Array.isArray(err.detail)) {
      return err.detail.map(function (d) {
        var field = d.loc && d.loc.length ? d.loc[d.loc.length - 1] : '';
        return (field ? field + ': ' : '') + (d.msg || String(d));
      }).join(' ');
    }
    if (typeof err.detail === 'string') return err.detail;
    return 'Greška';
  }

  function showToast(message, type) {
    if (!toastRoot || !message) return;
    var el = document.createElement('div');
    el.className = 'toast toast-' + (type || 'info');
    el.textContent = message;
    toastRoot.appendChild(el);
    setTimeout(function () { el.remove(); }, 4500);
  }

  function setFormBusy(form, busy, submitBtn) {
    if (!form) return;
    var buttons = form.querySelectorAll('button, input, select, textarea');
    buttons.forEach(function (el) { el.disabled = !!busy; });
    if (submitBtn) {
      submitBtn.dataset.originalText = submitBtn.dataset.originalText || submitBtn.textContent;
      submitBtn.textContent = busy ? 'Slanje...' : submitBtn.dataset.originalText;
    }
  }

  function statusLabel(status) {
    var map = {
      pending: 'Na čekanju',
      confirmed: 'Potvrđeno',
      rejected: 'Odbijeno',
      cancelled: 'Otkazano',
    };
    return map[status] || status;
  }

  function statusBadge(status) {
    var cls = 'badge badge-' + (status || 'pending');
    return '<span class="' + cls + '">' + statusLabel(status) + '</span>';
  }

  function getShownNotificationIds() {
    try {
      var raw = sessionStorage.getItem(NOTIFICATION_POPUP_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }

  function markNotificationPopupShown(notificationId) {
    var ids = getShownNotificationIds();
    if (ids.indexOf(notificationId) === -1) ids.push(notificationId);
    sessionStorage.setItem(NOTIFICATION_POPUP_KEY, JSON.stringify(ids));
  }

  function reservationDetailRows(r, venueName) {
    var dateStr = r.date ? String(r.date).slice(0, 10) : '';
    var startStr = r.start_time ? String(r.start_time).slice(11, 16) : '';
    var displayVenue = venueName || r.venue_name || ('Lokal #' + r.venue_id);
    var venuePhone = r.venue_phone;
    if (!venuePhone && r.venue_id && cachedVenues.length) {
      var v = cachedVenues.find(function (x) { return x.id === r.venue_id; });
      if (v && v.phone) venuePhone = v.phone;
    }
    var rows = [
      { label: 'Termin', value: dateStr + ', ' + startStr },
      { label: 'Lokal', value: displayVenue },
    ];
    if (venuePhone) rows.push({ label: 'Telefon lokala', value: venuePhone });
    if (r.guest_count) rows.push({ label: 'Broj gostiju', value: String(r.guest_count) });
    if (r.notes) rows.push({ label: 'Napomena', value: r.notes });
    if (r.table_number) rows.push({ label: 'Sto', value: 'Broj ' + r.table_number });
    return rows;
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

  function statusIconChar(kind) {
    if (kind === 'confirmed') return 'OK';
    if (kind === 'rejected') return 'X';
    if (kind === 'cancelled') return '-';
    return '!';
  }

  function setPendingBannerVisible(show) {
    if (pendingReservationBanner) {
      pendingReservationBanner.classList.toggle('hidden', !show);
    }
  }

  function showStatusResult(kind, title, lead, detailRows) {
    if (!confirmedPopup || !confirmedPopupBox) return;
    confirmedPopupBox.className = 'popup-box status-result';
    if (kind === 'confirmed') confirmedPopupBox.classList.add('confirmed');
    else if (kind === 'rejected') confirmedPopupBox.classList.add('rejected');
    else if (kind === 'cancelled') confirmedPopupBox.classList.add('cancelled');
    if (confirmedPopupIcon) confirmedPopupIcon.textContent = statusIconChar(kind);
    if (confirmedPopupTitle) confirmedPopupTitle.textContent = title;
    if (confirmedPopupLead) {
      confirmedPopupLead.textContent = lead || '';
      confirmedPopupLead.classList.toggle('hidden', !lead);
    }
    fillDetailsList(confirmedPopupDetails, detailRows);
    confirmedPopup.classList.remove('hidden');
  }

  function showGuestReservationOutcome(r, opts) {
    if (!r) return;
    opts = opts || {};
    if (r.status === 'confirmed') {
      showStatusResult(
        'confirmed',
        'Rezervacija potvrđena',
        opts.notificationMessage || 'Lokal je prihvatio tvoj zahtev. Vidimo se u rezervisanom terminu.',
        reservationDetailRows(r)
      );
    } else if (r.status === 'rejected') {
      var lead = opts.notificationMessage
        || 'Nažalost, lokal nije mogao da prihvati ovaj termin.';
      showStatusResult(
        'rejected',
        'Rezervacija odbijena',
        lead,
        reservationDetailRows(r)
      );
    }
  }

  function closeConfirmedPopup() {
    if (confirmedPopup) confirmedPopup.classList.add('hidden');
  }

  function closeActionConfirmModal() {
    if (actionConfirmModal) actionConfirmModal.classList.add('hidden');
    pendingActionConfirm = null;
    if (actionConfirmOk) {
      actionConfirmOk.disabled = false;
      actionConfirmOk.textContent = 'Otkaži rezervaciju';
    }
  }

  function openActionConfirm(options) {
    if (!actionConfirmModal) {
      if (options.onConfirm) options.onConfirm();
      return;
    }
    pendingActionConfirm = options;
    if (actionConfirmTitle) {
      actionConfirmTitle.textContent = options.title || 'Potvrda';
    }
    if (actionConfirmMessage) {
      actionConfirmMessage.textContent = options.message || '';
      actionConfirmMessage.classList.toggle('hidden', !options.message);
    }
    fillDetailsList(actionConfirmDetails, options.details || []);
    if (actionConfirmOk) {
      actionConfirmOk.textContent = options.confirmLabel || 'Otkaži rezervaciju';
      actionConfirmOk.className = 'btn ' + (options.confirmClass || 'btn-danger');
    }
    actionConfirmModal.classList.remove('hidden');
  }

  function openCancelReservationConfirm(r) {
    var venueName = r.venue_name || ('Lokal #' + r.venue_id);
    var lead = r.status === 'confirmed'
      ? 'Lokal će biti obavešten o otkazu. Ova akcija se ne može poništiti.'
      : 'Zahtev na čekanju biće povučen. Ova akcija se ne može poništiti.';
    openActionConfirm({
      title: 'Otkazati rezervaciju?',
      message: lead,
      details: reservationDetailRows(r, venueName),
      confirmLabel: 'Da, otkaži',
      confirmClass: 'btn-danger',
      onConfirm: function () {
        return api('/reservations/' + r.id, { method: 'DELETE' })
          .then(function () {
            closeActionConfirmModal();
            showStatusResult(
              'cancelled',
              'Rezervacija otkazana',
              'Termin više nije rezervisan.',
              reservationDetailRows(r, venueName)
            );
            loadMyReservations();
            loadNotifications();
          });
      },
    });
  }

  function getToken() {
    return sessionStorage.getItem(TOKEN_KEY);
  }

  function setToken(token) {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  }

  function showAuth(show) {
    authSection.classList.toggle('hidden', !!show);
    userInfo.classList.toggle('hidden', !show);
    reservationSection.classList.toggle('hidden', !show);
    if (!show) closeNotifPanel();
  }

  function closeNotifPanel() {
    if (notifPanel) notifPanel.classList.add('hidden');
    if (btnNotifications) btnNotifications.setAttribute('aria-expanded', 'false');
  }

  function toggleNotifPanel() {
    if (!notifPanel || !btnNotifications) return;
    var open = notifPanel.classList.contains('hidden');
    if (open) {
      notifPanel.classList.remove('hidden');
      btnNotifications.setAttribute('aria-expanded', 'true');
      loadNotifications();
    } else {
      closeNotifPanel();
    }
  }

  function setUser(user) {
    usernameSpan.textContent = user.username || user.name || '';
    if (userRole) {
      userRole.textContent = 'Gost';
      userRole.classList.remove('hidden');
    }
  }

  function api(url, options) {
    options = options || {};
    const token = getToken();
    const headers = Object.assign(
      { 'Content-Type': 'application/json' },
      token ? { Authorization: 'Bearer ' + token } : {},
      options.headers || {}
    );
    return fetch(API_BASE + url, Object.assign({}, options, { headers }))
      .then(async function (res) {
        const data = await res.json().catch(function () { return {}; });
        if (!res.ok) throw Object.assign({ status: res.status }, data);
        return data;
      });
  }

  function stopPolling() {
    if (pollIntervalId) {
      clearInterval(pollIntervalId);
      pollIntervalId = null;
    }
    sessionStorage.removeItem(POLL_RESERVATION_KEY);
    setPendingBannerVisible(false);
  }

  function pollForReservationStatus(reservationId) {
    stopPolling();
    if (reservationId == null) return;
    sessionStorage.setItem(POLL_RESERVATION_KEY, String(reservationId));
    setPendingBannerVisible(true);
    var attempts = 0;
    var maxAttempts = 30;

    function check() {
      attempts++;
      api('/reservations/' + reservationId)
        .then(function (r) {
          loadMyReservations();
          loadNotifications();
          if (r.status && r.status !== 'pending') {
            stopPolling();
            if (r.status === 'confirmed' || r.status === 'rejected') {
              showGuestReservationOutcome(r);
            }
          } else if (attempts >= maxAttempts) {
            stopPolling();
          }
        })
        .catch(function () {
          if (attempts >= maxAttempts) stopPolling();
        });
    }

    check();
    pollIntervalId = setInterval(check, 2000);
  }

  function loadNotifications() {
    if (!notificationsList) return;
    return api('/notifications/')
      .then(function (items) {
        notificationsList.innerHTML = '';
        var unread = 0;
        if (!Array.isArray(items) || items.length === 0) {
          if (notificationsEmpty) notificationsEmpty.classList.remove('hidden');
          if (notifUnreadBadge) notifUnreadBadge.classList.add('hidden');
          return;
        }
        if (notificationsEmpty) notificationsEmpty.classList.add('hidden');
        var shownIds = getShownNotificationIds();
        items.forEach(function (n) {
          if (!n.read) unread++;
          var li = document.createElement('li');
          li.className = 'notif-item kind-' + (n.kind || '') + (n.read ? ' read' : ' unread');
          li.textContent = n.message || n.kind;
          if (!n.read) {
            li.addEventListener('click', function () {
              api('/notifications/' + n.id + '/read', { method: 'PATCH' }).then(loadNotifications);
            });
          }
          notificationsList.appendChild(li);
        });
        if (notifUnreadBadge) {
          if (unread > 0) {
            notifUnreadBadge.textContent = String(unread);
            notifUnreadBadge.classList.remove('hidden');
          } else {
            notifUnreadBadge.classList.add('hidden');
          }
        }
        var firstUnread = items.find(function (n) {
          return !n.read && shownIds.indexOf(n.id) === -1;
        });
        if (!firstUnread) return;
        markNotificationPopupShown(firstUnread.id);
        if (firstUnread.kind === 'confirmed' || firstUnread.kind === 'rejected') {
          api('/reservations/' + firstUnread.reservation_id)
            .then(function (r) {
              showGuestReservationOutcome(r, { notificationMessage: firstUnread.message });
            })
            .catch(function () {
              showStatusResult(
                firstUnread.kind === 'confirmed' ? 'confirmed' : 'rejected',
                firstUnread.kind === 'confirmed' ? 'Rezervacija potvrđena' : 'Rezervacija odbijena',
                firstUnread.message || '',
                [{ label: 'Obaveštenje', value: firstUnread.message || '' }]
              );
            });
        }
      })
      .catch(function () {
        if (notificationsEmpty) {
          notificationsEmpty.textContent = 'Greška pri učitavanju obaveštenja.';
          notificationsEmpty.classList.remove('hidden');
        }
      });
  }

  function timeShort(t) {
    if (!t) return '';
    return String(t).slice(0, 5);
  }

  function timeToMinutes(hhmm) {
    if (!hhmm || hhmm.length < 4) return NaN;
    var parts = String(hhmm).split(':');
    return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
  }

  function minutesToHHMM(totalMin) {
    var h = Math.floor(totalMin / 60);
    var m = totalMin % 60;
    return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
  }

  function getSelectedVenue() {
    var venueEl = resVenue || formInput('res-venue');
    if (!venueEl || !venueEl.value) return null;
    var id = parseInt(venueEl.value, 10);
    if (!id) return null;
    return cachedVenues.find(function (x) { return x.id === id; }) || null;
  }

  function venueWindowForDate(venue, dateIso) {
    if (!venue || !dateIso) return { open: null, close: null };
    var d = new Date(dateIso + 'T12:00:00');
    var weekend = d.getDay() === 0 || d.getDay() === 6;
    return {
      open: timeShort(weekend ? venue.weekend_open : venue.weekday_open),
      close: timeShort(weekend ? venue.weekend_close : venue.weekday_close),
    };
  }

  /** Kraj termina za API (gost unosi samo početak; boravak 2h, skraćeno do zatvaranja). */
  function endTimeFromStart(startHHMM, hours, closeHHMM) {
    hours = hours == null ? DEFAULT_STAY_HOURS : hours;
    var startMin = timeToMinutes(startHHMM);
    if (isNaN(startMin)) return null;
    var endMin = startMin + hours * 60;
    var closeMin = closeHHMM ? timeToMinutes(closeHHMM) : NaN;
    if (!isNaN(closeMin) && endMin > closeMin) endMin = closeMin;
    if (endMin >= 24 * 60) endMin = 24 * 60 - 1;
    if (endMin <= startMin) return null;
    return minutesToHHMM(endMin);
  }

  function validateGuestReservationForm() {
    var dateVal = inputValue('res-date');
    var startVal = inputValue('res-start');
    if (!getSelectedVenue()) return 'Izaberite lokal.';
    if (!dateVal) return 'Izaberite datum.';
    if (!startVal) return 'Unesite vreme dolaska.';
    var venue = getSelectedVenue();
    var win = venueWindowForDate(venue, dateVal);
    var startMin = timeToMinutes(startVal);
    var openMin = timeToMinutes(win.open);
    var closeMin = timeToMinutes(win.close);
    if (!isNaN(openMin) && startMin < openMin) {
      return 'Vreme dolaska je pre otvaranja lokala (' + win.open + ').';
    }
    if (!isNaN(closeMin) && startMin >= closeMin) {
      return 'Vreme dolaska mora biti pre zatvaranja lokala (' + win.close + ').';
    }
    var end = endTimeFromStart(startVal, DEFAULT_STAY_HOURS, win.close);
    if (!end) {
      return 'Za boravak od 2 sata izaberite ranije vreme dolaska (mora stati u radno vreme lokala).';
    }
    return null;
  }

  function formatVenueHours(v) {
    if (!v) return '';
    return 'Pon-Pet ' + timeShort(v.weekday_open) + '-' + timeShort(v.weekday_close) +
      ', Vikend ' + timeShort(v.weekend_open) + '-' + timeShort(v.weekend_close);
  }

  function updateVenueHint() {
    if (!venueHint || !resVenue) return;
    var id = parseInt(resVenue.value, 10);
    var v = cachedVenues.find(function (x) { return x.id === id; });
    if (!v) {
      venueHint.classList.add('hidden');
      return;
    }
    venueHint.textContent = [v.address, v.city, v.phone, formatVenueHours(v)].filter(Boolean).join(' - ');
    venueHint.classList.remove('hidden');
  }

  function renderVenueCards(venues) {
    if (!venueCards) return;
    venueCards.innerHTML = '';
    if (!venues.length) {
      if (venueCardsEmpty) venueCardsEmpty.classList.remove('hidden');
      return;
    }
    if (venueCardsEmpty) venueCardsEmpty.classList.add('hidden');
    venues.forEach(function (v) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'venue-card';
      if (String(resVenue.value) === String(v.id)) btn.classList.add('selected');
      var contactLine = [v.phone, v.city, v.address].filter(Boolean).join(' · ');
      btn.innerHTML = '<p class="venue-card-title">' + escapeHtml(v.name) + '</p>' +
        '<p class="venue-card-meta">' + escapeHtml(contactLine) + '</p>' +
        '<p class="venue-card-meta muted">' + escapeHtml(formatVenueHours(v)) + '</p>';
      btn.addEventListener('click', function () {
        resVenue.value = String(v.id);
        document.querySelectorAll('.venue-card').forEach(function (c) { c.classList.remove('selected'); });
        btn.classList.add('selected');
        updateVenueHint();
      });
      venueCards.appendChild(btn);
    });
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function loadVenues() {
    return api('/venues/')
      .then(function (venues) {
        cachedVenues = venues || [];
        resVenue.innerHTML = '<option value="">Izaberi lokal</option>';
        cachedVenues.forEach(function (v) {
          var opt = document.createElement('option');
          opt.value = v.id;
          opt.textContent = v.name;
          resVenue.appendChild(opt);
        });
        renderVenueCards(cachedVenues);
        updateVenueHint();
      })
      .catch(function () {
        showToast('Ne mogu da učitam lokale.', 'error');
      });
  }

  function formatReservationLine(r) {
    var dateStr = r.date ? String(r.date).slice(0, 10) : '';
    var startStr = r.start_time ? String(r.start_time).slice(11, 16) : '';
    var venueName = r.venue_name || 'Lokal #' + r.venue_id;
    var tableTxt = r.table_number ? ', sto ' + r.table_number : '';
    return dateStr + ' ' + startStr + ' ' + venueName + tableTxt;
  }

  function loadMyReservations() {
    if (!myReservationsList) return;
    myReservationsEmpty.textContent = 'Nema rezervacija.';
    return api('/reservations/')
      .then(function (reservations) {
        myReservationsList.innerHTML = '';
        if (!Array.isArray(reservations) || !reservations.length) {
          myReservationsEmpty.classList.remove('hidden');
          return;
        }
        myReservationsEmpty.classList.add('hidden');
        reservations.forEach(function (r) {
          var li = document.createElement('li');
          li.className = 'res-item';
          var main = document.createElement('div');
          main.className = 'res-item-main';
          main.innerHTML = formatReservationLine(r) + ' ' + statusBadge(r.status);
          li.appendChild(main);
          if (r.status === 'pending' || r.status === 'confirmed') {
            var actions = document.createElement('div');
            actions.className = 'res-item-actions';
            if (r.status === 'pending') {
              var btnEdit = document.createElement('button');
              btnEdit.type = 'button';
              btnEdit.className = 'btn btn-secondary btn-sm';
              btnEdit.textContent = 'Izmeni';
              btnEdit.addEventListener('click', function () { openEditReservationModal(r); });
              actions.appendChild(btnEdit);
            }
            var btnCancel = document.createElement('button');
            btnCancel.type = 'button';
            btnCancel.className = 'btn btn-danger btn-sm';
            btnCancel.textContent = 'Otkaži';
            btnCancel.addEventListener('click', function () {
              openCancelReservationConfirm(r);
            });
            actions.appendChild(btnCancel);
            li.appendChild(actions);
          }
          myReservationsList.appendChild(li);
        });
      })
      .catch(function () {
        myReservationsEmpty.textContent = 'Greška pri učitavanju.';
        myReservationsEmpty.classList.remove('hidden');
      });
  }

  function openEditReservationModal(r) {
    if (!editResModal) return;
    editResModal.dataset.venueId = String(r.venue_id || '');
    document.getElementById('edit-res-id').value = r.id;
    document.getElementById('edit-res-date').value = r.date ? String(r.date).slice(0, 10) : '';
    document.getElementById('edit-res-date').min = todayIso();
    document.getElementById('edit-res-start').value = r.start_time ? String(r.start_time).slice(11, 16) : '';
    document.getElementById('edit-res-guests').value = r.guest_count || 2;
    document.getElementById('edit-res-notes').value = r.notes || '';
    document.getElementById('edit-res-error').classList.add('hidden');
    editResModal.classList.remove('hidden');
  }

  function closeEditReservationModal() {
    if (editResModal) editResModal.classList.add('hidden');
  }

  function enterApp(user) {
    setUser(user);
    showAuth(true);
    setMinReservationDate();
    loadNotifications();
    loadVenues().then(function () {
      loadMyReservations();
      var pendingPoll = sessionStorage.getItem(POLL_RESERVATION_KEY);
      if (pendingPoll) pollForReservationStatus(parseInt(pendingPoll, 10));
    });
  }

  document.querySelectorAll('.tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      var t = this.getAttribute('data-tab');
      document.querySelectorAll('.tab').forEach(function (x) { x.classList.remove('active'); });
      document.querySelector('.tab[data-tab="' + t + '"]').classList.add('active');
      document.getElementById('login-form').classList.toggle('hidden', t !== 'login');
      document.getElementById('register-form').classList.toggle('hidden', t !== 'register');
      loginError.classList.add('hidden');
      registerError.classList.add('hidden');
      if (registerSuccess) registerSuccess.classList.add('hidden');
    });
  });

  loginForm.addEventListener('submit', function (e) {
    e.preventDefault();
    loginError.classList.add('hidden');
    setFormBusy(loginForm, true, loginForm.querySelector('button[type="submit"]'));
    api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        username: loginUsername.value.trim(),
        password: loginPassword.value,
      }),
    })
      .then(function (data) {
        setToken(data.access_token);
        return api('/auth/me');
      })
      .then(enterApp)
      .catch(function (err) {
        loginError.textContent = formatApiError(err) || 'Pogrešno korisničko ime ili lozinka';
        loginError.classList.remove('hidden');
      })
      .finally(function () {
        setFormBusy(loginForm, false, loginForm.querySelector('button[type="submit"]'));
      });
  });

  registerForm.addEventListener('submit', function (e) {
    e.preventDefault();
    registerError.classList.add('hidden');
    if (registerSuccess) registerSuccess.classList.add('hidden');
    var regUser = document.getElementById('reg-username').value.trim();
    var regPass = document.getElementById('reg-password').value;
    setFormBusy(registerForm, true, registerForm.querySelector('button[type="submit"]'));
    api('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        username: regUser,
        password: regPass,
        name: document.getElementById('reg-name').value.trim(),
        phone: document.getElementById('reg-phone').value.trim(),
        email: document.getElementById('reg-email').value.trim(),
      }),
    })
      .then(function () {
        showToast('Nalog je kreiran. Prijavljujem...', 'success');
        return api('/auth/login', {
          method: 'POST',
          body: JSON.stringify({ username: regUser, password: regPass }),
        });
      })
      .then(function (data) {
        setToken(data.access_token);
        return api('/auth/me');
      })
      .then(enterApp)
      .catch(function (err) {
        registerError.textContent = formatApiError(err) || 'Greška pri registraciji';
        registerError.classList.remove('hidden');
      })
      .finally(function () {
        setFormBusy(registerForm, false, registerForm.querySelector('button[type="submit"]'));
      });
  });

  btnLogout.addEventListener('click', function () {
    stopPolling();
    setToken(null);
    setUser({ username: '' });
    showAuth(false);
    if (userRole) userRole.classList.add('hidden');
    if (resVenue) resVenue.innerHTML = '<option value="">Izaberi lokal</option>';
    if (reservationForm) reservationForm.reset();
    if (reservationError) reservationError.classList.add('hidden');
    if (reservationSuccess) reservationSuccess.classList.add('hidden');
  });

  if (resVenue) resVenue.addEventListener('change', updateVenueHint);

  if (btnRefreshReservations) {
    btnRefreshReservations.addEventListener('click', function () {
      loadMyReservations();
      loadNotifications();
    });
  }
  if (btnRefreshVenues) {
    btnRefreshVenues.addEventListener('click', function () {
      loadVenues().then(function () {
        showToast('Lista lokala je osvežena.', 'success');
      });
    });
  }

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState !== 'visible' || !getToken()) return;
    loadVenues();
    if (sessionStorage.getItem(POLL_RESERVATION_KEY)) {
      loadMyReservations();
      loadNotifications();
    }
  });
  if (btnRefreshNotifications) btnRefreshNotifications.addEventListener('click', loadNotifications);

  if (btnNotifications) btnNotifications.addEventListener('click', function (e) {
    e.stopPropagation();
    toggleNotifPanel();
  });

  document.addEventListener('click', function (e) {
    if (!notifPanel || notifPanel.classList.contains('hidden')) return;
    if (e.target.closest('.notif-bell-wrap')) return;
    closeNotifPanel();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    closeNotifPanel();
    closeActionConfirmModal();
    closeEditReservationModal();
    closeConfirmedPopup();
  });

  if (actionConfirmCancel) {
    actionConfirmCancel.addEventListener('click', closeActionConfirmModal);
  }
  if (actionConfirmModal) {
    actionConfirmModal.addEventListener('click', function (e) {
      if (e.target === actionConfirmModal) closeActionConfirmModal();
    });
  }
  if (actionConfirmOk) {
    actionConfirmOk.addEventListener('click', function () {
      if (!pendingActionConfirm || !pendingActionConfirm.onConfirm) return;
      actionConfirmOk.disabled = true;
      actionConfirmOk.textContent = 'Otkazujem…';
      Promise.resolve(pendingActionConfirm.onConfirm())
        .catch(function (err) {
          showToast(formatApiError(err), 'error');
          actionConfirmOk.disabled = false;
          actionConfirmOk.textContent = pendingActionConfirm.confirmLabel || 'Da, otkaži';
        });
    });
  }

  if (confirmedPopupClose) confirmedPopupClose.addEventListener('click', closeConfirmedPopup);
  if (confirmedPopup) {
    confirmedPopup.addEventListener('click', function (e) {
      if (e.target === confirmedPopup) closeConfirmedPopup();
    });
  }

  if (reservationForm) reservationForm.addEventListener('submit', function (e) {
    e.preventDefault();
    var errEl = reservationError || formInput('reservation-error');
    var okEl = reservationSuccess || formInput('reservation-success');
    if (errEl) errEl.classList.add('hidden');
    if (okEl) okEl.classList.add('hidden');
    var validationMsg = validateGuestReservationForm();
    if (validationMsg) {
      if (errEl) {
        errEl.textContent = validationMsg;
        errEl.classList.remove('hidden');
      }
      showToast(validationMsg, 'error');
      return;
    }
    var venue = getSelectedVenue();
    var dateVal = inputValue('res-date');
    var startVal = inputValue('res-start');
    var win = venueWindowForDate(venue, dateVal);
    var endTime = endTimeFromStart(startVal, DEFAULT_STAY_HOURS, win.close);
    var guestsRaw = inputValue('res-guests', '2');
    var notesRaw = inputValue('res-notes', '');
    setFormBusy(reservationForm, true, btnSubmitReservation);
    var payload = {
      venue_id: parseInt(inputValue('res-venue'), 10),
      date: dateVal,
      start_time: startVal,
      end_time: endTime,
      guest_count: parseInt(guestsRaw, 10) || 2,
      notes: notesRaw.trim() ? notesRaw.trim() : null,
    };
    api('/reservations/', { method: 'POST', body: JSON.stringify(payload) })
      .then(function (reservation) {
        if (okEl) {
          okEl.textContent = 'Zahtev je poslat. Čeka se odgovor lokala.';
          okEl.classList.remove('hidden');
        }
        showToast('Zahtev za rezervaciju je poslat.', 'success');
        reservationForm.reset();
        setMinReservationDate();
        loadMyReservations();
        pollForReservationStatus(reservation.id);
      })
      .catch(function (err) {
        var msg = formatApiError(err);
        if (errEl) {
          errEl.textContent = msg;
          errEl.classList.remove('hidden');
        }
        showToast(msg, 'error');
      })
      .finally(function () {
        setFormBusy(reservationForm, false, btnSubmitReservation);
      });
  });

  if (editResForm) {
    editResForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var errEl = document.getElementById('edit-res-error');
      errEl.classList.add('hidden');
      var id = document.getElementById('edit-res-id').value;
      var editDate = document.getElementById('edit-res-date').value;
      var editStart = document.getElementById('edit-res-start').value;
      var editVenueId = editResModal && editResModal.dataset.venueId
        ? parseInt(editResModal.dataset.venueId, 10)
        : NaN;
      var editVenue = cachedVenues.find(function (v) { return v.id === editVenueId; });
      var editWin = venueWindowForDate(editVenue, editDate);
      var editEnd = endTimeFromStart(editStart, DEFAULT_STAY_HOURS, editWin.close);
      if (!editEnd) {
        errEl.textContent = 'Za boravak od 2 sata izaberite ranije vreme dolaska.';
        errEl.classList.remove('hidden');
        return;
      }
      setFormBusy(editResForm, true, editResForm.querySelector('button[type="submit"]'));
      api('/reservations/' + id, {
        method: 'PATCH',
        body: JSON.stringify({
          date: editDate,
          start_time: editStart,
          end_time: editEnd,
          guest_count: parseInt(document.getElementById('edit-res-guests').value, 10),
          notes: document.getElementById('edit-res-notes').value.trim() || null,
        }),
      })
        .then(function () {
          showToast('Rezervacija je izmenjena.', 'success');
          closeEditReservationModal();
          loadMyReservations();
        })
        .catch(function (err) {
          errEl.textContent = formatApiError(err);
          errEl.classList.remove('hidden');
        })
        .finally(function () {
          setFormBusy(editResForm, false, editResForm.querySelector('button[type="submit"]'));
        });
    });
  }
  if (document.getElementById('edit-res-cancel')) {
    document.getElementById('edit-res-cancel').addEventListener('click', closeEditReservationModal);
  }
  if (editResModal) {
    editResModal.addEventListener('click', function (e) {
      if (e.target === editResModal) closeEditReservationModal();
    });
  }

  (function init() {
    setMinReservationDate();
    var token = getToken();
    if (!token) {
      showAuth(false);
      return;
    }
    api('/auth/me')
      .then(enterApp)
      .catch(function () {
        setToken(null);
        showAuth(false);
      });
  })();
})();
