import type { UserDTO } from '@optiagent/shared';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogFooter, DialogTitle } from '@/components/ui/dialog';
import { useDeactivateUserMutation } from '../api/usersApi';

interface DeactivateConfirmDialogProps {
  open: boolean;
  user: UserDTO | null;
  onClose: () => void;
}

export function DeactivateConfirmDialog({ open, user, onClose }: DeactivateConfirmDialogProps) {
  const [deactivate, { isLoading }] = useDeactivateUserMutation();

  const handleConfirm = async () => {
    if (!user) return;
    await deactivate(user.id).unwrap();
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogContent className="max-w-sm">
        <DialogTitle>Deactivate user?</DialogTitle>
        <p className="text-sm text-slate-600">
          <strong>{user?.email}</strong> will no longer be able to sign in. This can be reversed
          by editing the user.
        </p>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            className="bg-red-600 text-white hover:bg-red-700"
            onClick={() => void handleConfirm()}
            disabled={isLoading}
          >
            {isLoading ? 'Deactivating…' : 'Deactivate'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
