document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('conference-grid');
    const selectedList = document.getElementById('selected-conferences');
    const submitBtn = document.getElementById('submit-btn');

    // 서버에서 학회 데이터 가져오기
    fetch('/conferences')
        .then(response => response.json())
        .then(data => {
            createCheckboxes(data);
        })
        .catch(err => console.error('Error fetching conference data:', err));

    // 체크박스 생성 함수
    function createCheckboxes(data) {
        const groupedData = data.reduce((acc, row) => {
            const kind = row.kind;
            if (!acc[kind]) acc[kind] = [];
            acc[kind].push(row.conference);
            return acc;
        }, {});

        for (const kind in groupedData) {
            const card = document.createElement('div');
            card.classList.add('card');
            const cardTitle = document.createElement('h2');
            cardTitle.textContent = kind;
            card.appendChild(cardTitle);

            const checkboxGroup = document.createElement('div');
            checkboxGroup.classList.add('checkbox-group');

            groupedData[kind].forEach(conference => {
                const label = document.createElement('label');
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.classList.add('conference-checkbox');
                checkbox.value = conference;

                label.appendChild(checkbox);
                label.appendChild(document.createTextNode(conference));
                checkboxGroup.appendChild(label);
            });

            card.appendChild(checkboxGroup);
            grid.appendChild(card);
        }

        attachCheckboxListeners();
    }

    // 체크박스 선택 시 리스트 업데이트
    function attachCheckboxListeners() {
        const checkboxes = document.querySelectorAll('.conference-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                selectedList.innerHTML = '';
                const selected = Array.from(checkboxes)
                    .filter(cb => cb.checked)
                    .map(cb => cb.value);
                selected.forEach(conf => {
                    const li = document.createElement('li');
                    li.textContent = conf;
                    selectedList.appendChild(li);
                });
            });
        });
    }

    // 제출 버튼 클릭 이벤트
    submitBtn.addEventListener('click', () => {
        const form = document.getElementById('filter-form');
        const formData = new FormData(form);
        const filters = Object.fromEntries(formData.entries());
        const selectedConferences = Array.from(document.querySelectorAll('.conference-checkbox'))
            .filter(cb => cb.checked)
            .map(cb => cb.value);
        filters.selectedConferences = selectedConferences;

        // 입력값 검증
        if (!filters.option) {
            alert('옵션을 선택해주세요');
            return;
        }

        if (!filters.startyear || !filters.endyear) {
            alert('시작 연도와 종료 연도를 입력해주세요');
            return;
        }

        const startyear = parseInt(filters.startyear, 10);
        const endyear = parseInt(filters.endyear, 10);

        if (startyear > endyear) {
            alert('시작 연도는 종료 연도보다 작거나 같아야 합니다');
            return;
        }

        if (selectedConferences.length === 0) {
            alert('최소 하나 이상의 학회를 선택해주세요!');
            return;
        }

        // 데이터 제출
        console.log('Submitted Data:', filters);

        // 서버로 데이터 전송 (예시)
        fetch('/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(filters),
        })
            .then(response => response.json())
            .then(data => console.log('Server Response:', data))
            .catch(err => console.error('Error:', err));
    });
});

// 토글 버튼 동작
const toggleSelectBtn = document.getElementById('toggle-select-btn');
let allSelected = false; // 선택 상태 추적 변수

toggleSelectBtn.addEventListener('click', () => {
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    allSelected = !allSelected; // 상태 반전

    checkboxes.forEach(checkbox => {
        checkbox.checked = allSelected; // 모든 체크박스의 상태를 변경
    });

    // 버튼 텍스트 변경
    toggleSelectBtn.textContent = allSelected ? '모두 해제' : '모두 선택';
});
