//can be used to change displayed time from relative to absolute
//ie. for github when you need to do screenshot audits. 
// either paste into console or save as a bookmarklet

javascript:(function() {
    var els = window.document.querySelectorAll("time-ago,relative-time");
    els.forEach(function(el) {
        el.innerHTML = el._date; 
        el.disconnectedCallback();
    });
})();
