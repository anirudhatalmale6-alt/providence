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
