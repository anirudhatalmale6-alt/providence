/* Providence — the small amount of behaviour the site needs.
   The brief asks for no excessive animation, so this does three things only:
   the mobile menu, the year in the footer, and holding enquiry forms until a
   booking system exists. */
(function () {
  'use strict';

  var burger = document.getElementById('burger');
  var mob = document.getElementById('mobnav');
  if (burger && mob) {
    burger.addEventListener('click', function () {
      var open = mob.classList.toggle('open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  var yr = document.getElementById('yr');
  if (yr) yr.textContent = new Date().getFullYear();

  /* Every form on the site is a real form with real fields, but there is no
     destination for it yet. Rather than fail silently or pretend to send, it
     says plainly what happens next — and the markup is ready for whichever
     booking or enquiry system gets connected. */
  function hold(form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var done = form.querySelector('.form-done');
      if (!done) {
        done = document.createElement('div');
        done.className = 'form-done note';
        done.style.marginTop = '22px';
        done.innerHTML = '<span class="caps">Not yet connected</span>' +
          '<p>This form is built and ready. It needs an address to deliver to &mdash; ' +
          'once the Providence mailbox or booking system is set up, this sends straight there.</p>';
        form.appendChild(done);
      }
      done.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    });
  }
  Array.prototype.forEach.call(document.querySelectorAll('form'), hold);
})();

/* ---------------------------------------------------------------------------
   Providence Concierge.

   A scripted concierge, not a language model. Two reasons: it costs Shaazia
   nothing to run, and it cannot invent an availability, a rate or a policy —
   which matters on a hospitality site where a wrong answer becomes a booking
   dispute. Everything below answers from the site's own facts, and anything
   it does not know is handed to a human rather than guessed at.

   To make it a real AI agent later, replace reply() with a fetch to an
   endpoint. Nothing else changes.
   --------------------------------------------------------------------------- */
(function () {
  'use strict';
  var root = document.getElementById('concierge');
  if (!root) return;

  var openBtn = document.getElementById('concOpen');
  var panel = document.getElementById('concPanel');
  var closeBtn = document.getElementById('concClose');
  var log = document.getElementById('concLog');
  var chips = document.getElementById('concChips');
  var form = document.getElementById('concForm');
  var input = document.getElementById('concInput');

  var here = location.pathname.replace(/\/$/, '').split('/').pop() || 'index.html';
  var deep = location.pathname.indexOf('/residences/') > -1 ? '../' : '';

  var KNOWN = [
    { k: ['book', 'booking', 'reserve', 'availability', 'available', 'dates'],
      a: 'Tell us your dates and we confirm availability, the nightly rate, any minimum stay and '
       + 'the cancellation terms in writing before anything is paid.',
      cta: ['Request your stay', deep + 'book.html'] },
    { k: ['corporate', 'business', 'company', 'contractor', 'relocat', 'long stay', 'extended',
          'month', 'invoice'],
      a: 'Extended and corporate stays are arranged directly with us — invoiced to the company, '
       + 'with weekly and monthly rates and one point of contact throughout.',
      cta: ['Corporate & extended stays', deep + 'corporate-stays.html'] },
    { k: ['landlord', 'owner', 'my property', 'partner', 'manage my'],
      a: 'Providence works with a small number of selected owners and takes responsibility for the '
       + 'presentation of the property, the guests in it and its condition afterwards.',
      cta: ['Property partners', deep + 'property-partners.html'] },
    { k: ['where', 'location', 'area', 'vauxhall', 'london', 'dubai', 'coming', 'soon', 'next'],
      a: 'The first residence is in Vauxhall, London SW8. Further residences are being prepared '
       + 'across central London, with a first collection in Dubai.',
      cta: ['The Providence Collection', deep + 'residences.html'] },
    { k: ['check in', 'check-in', 'checkin', 'arrive', 'arrival', 'check out', 'checkout', 'key'],
      a: 'Check-in is from 15:00 by self check-in, and check-out is by 11:00. Earlier arrival or a '
       + 'later departure can often be arranged — just ask when you book.' },
    { k: ['wifi', 'wi-fi', 'internet', 'broadband', 'work', 'desk'],
      a: 'Every residence has fast fibre broadband and a proper desk. The connection details are in '
       + 'the welcome note when you arrive.' },
    { k: ['park', 'parking', 'car'],
      a: 'On-street parking by permit, arranged on request. Tell us if you are bringing a car and we '
       + 'will sort it before you arrive.' },
    { k: ['pet', 'dog', 'cat'],
      a: 'Pets by prior arrangement only — do ask, and we will tell you what is possible at the '
       + 'residence you have in mind.' },
    { k: ['smok', 'party', 'event', 'rules'],
      a: 'No smoking anywhere in the residence, and no parties or events. Quiet between 22:00 and '
       + '08:00, in fairness to the neighbours.' },
    { k: ['cancel', 'refund', 'deposit'],
      a: 'Cancellation windows and any deposit are confirmed in writing at the time of booking and '
       + 'before any payment is taken.',
      cta: ['Booking terms', deep + 'booking-terms.html'] },
    { k: ['price', 'rate', 'cost', 'how much', 'nightly'],
      a: 'Rates depend on the dates and the length of stay, so they are quoted rather than listed. '
       + 'Send us your dates and we will come straight back with a figure.',
      cta: ['Request your stay', deep + 'book.html'] },
    { k: ['clean', 'housekeep', 'linen', 'towel'],
      a: 'Residences are professionally cleaned before every arrival, with pressed cotton linen. On '
       + 'stays of a week or more, housekeeping and fresh linen are included weekly.' },
    { k: ['phone', 'call', 'contact', 'email', 'speak', 'human'],
      a: 'You can call us on 07455 125635, or send an enquiry and a person will reply — usually the '
       + 'same day and always within one working day.',
      cta: ['Contact Providence', deep + 'contact.html'] }
  ];

  var CHIPS = ['Availability', 'Corporate stays', 'Where are you?', 'Check-in times', 'I own a property'];

  function bubble(who, text, cta) {
    var d = document.createElement('div');
    d.className = 'conc-msg ' + who;
    d.textContent = text;
    if (cta) {
      var a = document.createElement('a');
      a.className = 'conc-cta';
      a.href = cta[1];
      a.textContent = cta[0];
      d.appendChild(a);
    }
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
  }

  function reply(q) {
    var s = q.toLowerCase();
    for (var i = 0; i < KNOWN.length; i++) {
      for (var j = 0; j < KNOWN[i].k.length; j++) {
        if (s.indexOf(KNOWN[i].k[j]) > -1) return KNOWN[i];
      }
    }
    /* Not known — hand it to a person rather than improvise. */
    return {
      a: 'That one is better answered by a person than by me. Send it across and we will come back '
       + 'to you, usually the same day.',
      cta: ['Contact Providence', deep + 'contact.html']
    };
  }

  function ask(q) {
    bubble('me', q);
    chips.innerHTML = '';
    setTimeout(function () {
      var r = reply(q);
      bubble('them', r.a, r.cta);
    }, 420);
  }

  var started = false;
  function start() {
    if (started) return;
    started = true;
    bubble('them', 'Good day — welcome to Providence. Ask about availability, a longer stay, or '
                 + 'anything about the residences.');
    CHIPS.forEach(function (c) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'conc-chip';
      b.textContent = c;
      b.addEventListener('click', function () { ask(c); });
      chips.appendChild(b);
    });
  }

  function toggle(open) {
    panel.hidden = !open;
    openBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    root.classList.toggle('open', open);
    if (open) { start(); setTimeout(function () { input.focus(); }, 80); }
  }

  openBtn.addEventListener('click', function () { toggle(panel.hidden); });
  closeBtn.addEventListener('click', function () { toggle(false); });
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var v = input.value.trim();
    if (!v) return;
    input.value = '';
    ask(v);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !panel.hidden) toggle(false);
  });
})();

/* ---------------------------------------------------------------------------
   Motion. Slow, one-way, and off entirely for prefers-reduced-motion.

   IntersectionObserver rather than a scroll handler: the browser does the
   work off the main thread, which matters because her point 17 asks that
   none of this cost mobile performance.
   --------------------------------------------------------------------------- */
(function () {
  'use strict';
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var els = document.querySelectorAll('.reveal, .zoom');

  if (reduce || !('IntersectionObserver' in window)) {
    /* Show everything immediately. A page that needs JavaScript to become
       readable is broken, not animated. */
    Array.prototype.forEach.call(els, function (el) { el.classList.add('in'); });
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.classList.add('in');
        io.unobserve(e.target);      /* one-way; never animates back out */
      }
    });
  }, { rootMargin: '0px 0px -12% 0px', threshold: 0.08 });

  Array.prototype.forEach.call(els, function (el) { io.observe(el); });

})();
