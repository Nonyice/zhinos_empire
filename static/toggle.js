function toggleMenu() {
    // Toggle the "active" class on the navigation menu
    const nav = document.querySelector('nav');
    nav.classList.toggle('active');

    // Change the hamburger icon to 'X' when menu is active
    const bars = document.querySelectorAll('.hamburger .bar');
    bars.forEach(bar => {
        bar.style.transition = 'all 0.3s ease';
    });

    if (nav.classList.contains('active')) {
        // Change hamburger to 'X'
        bars[0].style.transform = 'rotate(45deg) translateY(7px)';
        bars[1].style.opacity = '0';
        bars[2].style.transform = 'rotate(-45deg) translateY(-7px)';
    } else {
        // Revert hamburger to normal
        bars[0].style.transform = 'rotate(0)';
        bars[1].style.opacity = '1';
        bars[2].style.transform = 'rotate(0)';
    }
}
