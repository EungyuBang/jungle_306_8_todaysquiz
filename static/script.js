function register() {
  let inputId = $("#id-input").val();
  let inputPw = $("#pw-input").val();
  let inputName = $("#name-input").val();

  $.ajax({
    type: "POST",
    url: "/register",
    data: {inputId: inputId, inputPw: inputPw, inputName: inputName},
    success: function (response) {
      if (response["result"] == "success") {
        alert("회원가입 성공!");
        window.location.href = "/";
      } else {
        alert(response['msg']);
      }
    },
  });
}

function login() {
  let userId = $(".id-input").val();
  let userPw = $(".pw-input").val();

  $.ajax({
    type: "POST",
    url: "/login",
    data: {userId: userId, userPw: userPw},
    success: function (response) {
      if (response["result"] == "success") {
        localStorage.setItem("token", response["access_token"]);
        alert("로그인 성공!");
        window.location.href = "afterLogin";
      } else {
        alert(response['msg']);
      }
    },
  });
}