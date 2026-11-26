document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.querySelector('input[type="file"]');
  const fileName = document.getElementById("fileName");
  if (fileInput && fileName) {
    fileInput.addEventListener("change", () => {
      fileName.textContent = fileInput.files.length ? fileInput.files[0].name : "or drop your resume here";
    });
  }
  document.querySelectorAll(".flash").forEach((item) => {
    setTimeout(() => { item.style.opacity = "0"; item.style.transform = "translateY(-8px)"; }, 4200);
    setTimeout(() => item.remove(), 4800);
  });
});
