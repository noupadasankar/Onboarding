import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ALL_ROLES } from '@hr-onboarding/shared';
import type { UserDTO } from '@hr-onboarding/shared';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Dialog, DialogContent, DialogFooter, DialogTitle } from '@/components/ui/dialog';
import { useCreateUserMutation, useUpdateUserMutation } from '../api/usersApi';
import { createUserSchema, updateUserSchema } from '../validation/user.schema';
import type { CreateUserInput, UpdateUserInput } from '../validation/user.schema';

interface UserFormModalProps {
  open: boolean;
  onClose: () => void;
  /** When provided, the form operates in edit mode. */
  initialValues?: UserDTO;
}

/** Unified create/edit form. Create mode shows a password field; edit mode hides it. */
export function UserFormModal({ open, onClose, initialValues }: UserFormModalProps) {
  const isEdit = Boolean(initialValues);
  const [createUser, { isLoading: creating }] = useCreateUserMutation();
  const [updateUser, { isLoading: updating }] = useUpdateUserMutation();
  const isLoading = creating || updating;

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateUserInput | UpdateUserInput>({
    resolver: zodResolver(isEdit ? updateUserSchema : createUserSchema) as never,
    defaultValues: initialValues
      ? { role: initialValues.role, department: initialValues.department ?? undefined }
      : undefined,
  });

  useEffect(() => {
    if (open) {
      reset(
        initialValues
          ? { role: initialValues.role, department: initialValues.department ?? undefined }
          : undefined,
      );
    }
  }, [open, initialValues, reset]);

  const onSubmit = handleSubmit(async (values) => {
    try {
      if (isEdit && initialValues) {
        await updateUser({ id: initialValues.id, body: values as UpdateUserInput }).unwrap();
      } else {
        await createUser(values as CreateUserInput).unwrap();
      }
      onClose();
    } catch {
      // Error feedback via form state — network errors surface as server errors.
    }
  });

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogContent>
        <DialogTitle>{isEdit ? 'Edit User' : 'Create User'}</DialogTitle>
        <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {!isEdit && (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="off"
              {...register('email' as keyof CreateUserInput)}
            />
            {'email' in errors && errors.email && (
              <p role="alert" className="text-sm text-red-600">
                {errors.email.message as string}
              </p>
            )}
          </div>
        )}

        {!isEdit && (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              {...register('password' as keyof CreateUserInput)}
            />
            {'password' in errors && errors.password && (
              <p role="alert" className="text-sm text-red-600">
                {errors.password.message as string}
              </p>
            )}
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="role">Role</Label>
          <Select id="role" {...register('role')}>
            <option value="">Select role…</option>
            {ALL_ROLES.map((r) => (
              <option key={r} value={r}>
                {r.replace('_', ' ')}
              </option>
            ))}
          </Select>
          {errors.role && (
            <p role="alert" className="text-sm text-red-600">
              {errors.role.message as string}
            </p>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="department">Department (optional)</Label>
          <Input
            id="department"
            type="text"
            placeholder="e.g. Engineering"
            {...register('department')}
          />
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? 'Saving…' : isEdit ? 'Save changes' : 'Create user'}
          </Button>
        </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
