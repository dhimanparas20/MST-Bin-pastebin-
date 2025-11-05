document.addEventListener('DOMContentLoaded', () => {
    const pasteArea = document.getElementById('pasteArea');
    const lineNumbers = document.getElementById('lineNumbers');
    const saveBtn = document.getElementById('saveBtn');

    function updateLineNumbers() {
        const lines = pasteArea.value.split('\n').length;
        lineNumbers.innerHTML = Array(lines).fill(0).map((_, i) => `${i + 1}<br>`).join('');
    }

    pasteArea.addEventListener('input', updateLineNumbers);
    pasteArea.addEventListener('scroll', () => {
        lineNumbers.scrollTop = pasteArea.scrollTop;
    });

    updateLineNumbers();

    function savePaste() {
        const data = pasteArea.value;
        const headingInput = document.getElementById('pasteHeading');
        let heading = headingInput.value.trim();
        if (!data.trim()) {
            alert('Please enter some text before saving.');
            return;
        }
        if (!heading) heading = "My Paste";

        fetch('/api/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ data, heading }),
        })
        .then(response => response.json())
        .then(result => {
            if (result.url) {
                window.location.href = result.url;
            } else {
                alert('Error saving paste. Please try again.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error saving paste. Please try again.');
        });
    }

    saveBtn.addEventListener('click', savePaste);

    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            savePaste();
        }
    });
});