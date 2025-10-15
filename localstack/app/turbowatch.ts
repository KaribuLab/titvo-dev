import { defineConfig } from 'turbowatch';

export default defineConfig({
  project: __dirname,
  triggers: [
    {
      expression: ['match', '*.ts', 'basename'],
      name: 'deploy',
      onChange: async ({ spawn }) => {
        await spawn`rm -rf cdk.out && tsc`;
        await spawn`cdklocal deploy --require-approval=never`;
      },
    },
  ],
});