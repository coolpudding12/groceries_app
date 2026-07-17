export async function onRequest(context) {
  // Extract the authorization_id from the URL query parameters
  const { searchParams } = new URL(context.request.url);
  const authorizationId = searchParams.get('authorization_id');

  // Redirect to your login page with the authorization_id preserved
  return Response.redirect(`https://grocerylist.devkeo.com/login?authorization_id=${authorizationId}`, 302);
}