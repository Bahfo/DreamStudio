const header = document.querySelector('.index_header');

header.addEventListener('mousemove', (e) => {
    const rect = header.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    header.style.setProperty('--x', `${x}px`);
    header.style.setProperty('--y', `${y}px`);
});

window.addEventListener('scroll', () => {
    const sections = document.querySelectorAll('section');
    
    sections.forEach((section) => {
        const rect = section.getBoundingClientRect();
        const content = section.querySelector('.section-content');
        
        if (!content) return;
        let scrollFraction = Math.max(0, Math.min(1, Math.abs(rect.top) / window.innerHeight));
        
        if (rect.top <= 0) {
            let scaleVal = 1 - (scrollFraction * 0.3); 
            let opacityVal = 1 - (scrollFraction * 1.2); 

            content.style.transform = `scale(${scaleVal})`;
            content.style.opacity = opacityVal;
        } else {
            content.style.transform = `scale(1)`;
            content.style.opacity = 1;
        }
    });
});