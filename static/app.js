document.getElementById('uploadForm').addEventListener('submit', function(e) {
  e.preventDefault();

  // Hide previous results and errors, show loading spinner
  document.getElementById('loading').style.display = 'block';
  document.getElementById('result').style.display = 'none';
  document.getElementById('error').style.display = 'none';
  document.getElementById('improvementTips').style.display = 'none';

  const formData = new FormData();
  formData.append('resume', document.getElementById('resume').files[0]);
  formData.append('job_description', document.getElementById('job_description').files[0]);

  fetch('/ats_score', {
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    document.getElementById('loading').style.display = 'none';
    if (data.error) {
      document.getElementById('error').innerText = data.error;
      document.getElementById('error').style.display = 'block';
    } else {
      document.getElementById('atsScore').innerText = data.ats_score;
      document.getElementById('result').style.display = 'block';
      if (data.improvement_tips && data.improvement_tips.length > 0) {
        let tipsContainer = document.getElementById('improvementTips');
        let tipsHTML = "<h3>Improvement Tips:</h3><ul>";
        data.improvement_tips.forEach(tip => {
          tipsHTML += `<li>${tip}</li>`;
        });
        tipsHTML += "</ul>";
        tipsContainer.innerHTML = tipsHTML;
        tipsContainer.style.display = 'block';
      }
    }
  })
  .catch(error => {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('error').innerText = 'An error occurred. Please try again.';
    document.getElementById('error').style.display = 'block';
    console.error('Error:', error);
  });
});
