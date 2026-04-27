import newPassword from "@/app/(auth)/newpassword/page";

export async function loginUser(email: string, password: string) {
  await new Promise(resolve => setTimeout(resolve, 1500));
  console.log(`Login: ${email}`);
  return { success: true };
}

export async function sendResetOTP(email: string) {
  await new Promise(resolve => setTimeout(resolve, 1500));
  console.log(`OTP sent to: ${email}`);
  return { success: true };
}
export async function changePassword(newpassword : string){
  await new Promise(resolve => setTimeout(resolve , 1500));
  console.log(`password changed to : ${newpassword}`);
  return {success : true}
}