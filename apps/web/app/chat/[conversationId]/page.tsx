import { ChatScreen } from "@/components/chat/chat-screen";

export default async function ChatPage({ params }: { params: Promise<{ conversationId: string }> }) {
  const { conversationId } = await params;
  return <ChatScreen conversationId={conversationId} />;
}
