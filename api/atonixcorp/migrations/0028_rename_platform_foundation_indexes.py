from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0027_platform_foundation_canonical_fields'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='platformauditevent',
            new_name='finances_pl_domain_d56f1c_idx',
            old_name='fin_platf_domain_f9132d_idx',
        ),
        migrations.RenameIndex(
            model_name='platformauditevent',
            new_name='finances_pl_organiz_3daa3a_idx',
            old_name='fin_platf_organiz_5d93c2_idx',
        ),
        migrations.RenameIndex(
            model_name='platformauditevent',
            new_name='finances_pl_workspa_60cc6f_idx',
            old_name='fin_platf_workspa_e265f7_idx',
        ),
        migrations.RenameIndex(
            model_name='platformauditevent',
            new_name='finances_pl_resourc_eac5ec_idx',
            old_name='fin_platf_resourc_e836f1_idx',
        ),
        migrations.RenameIndex(
            model_name='platformauditevent',
            new_name='finances_pl_subject_d66fc2_idx',
            old_name='fin_platf_subject_e6bf86_idx',
        ),
        migrations.RenameIndex(
            model_name='platformauditevent',
            new_name='finances_pl_actor_i_78e75e_idx',
            old_name='fin_platf_actor_i_c9c1f4_idx',
        ),
        migrations.RenameIndex(
            model_name='platformauditevent',
            new_name='finances_pl_action_b31759_idx',
            old_name='fin_platf_action__8d5bfe_idx',
        ),
        migrations.RenameIndex(
            model_name='platformauditevent',
            new_name='finances_pl_correla_9dc98e_idx',
            old_name='fin_platf_correla_ef4ef2_idx',
        ),
        migrations.RenameIndex(
            model_name='platformtask',
            new_name='finances_pl_domain_be52bf_idx',
            old_name='fin_platf_domain_95f775_idx',
        ),
        migrations.RenameIndex(
            model_name='platformtask',
            new_name='finances_pl_organiz_9da274_idx',
            old_name='fin_platf_organiz_1cf804_idx',
        ),
        migrations.RenameIndex(
            model_name='platformtask',
            new_name='finances_pl_workspa_75b65a_idx',
            old_name='fin_platf_workspa_7ea255_idx',
        ),
        migrations.RenameIndex(
            model_name='platformtask',
            new_name='finances_pl_assigne_d1fce3_idx',
            old_name='fin_platf_assigne_5f14f0_idx',
        ),
        migrations.RenameIndex(
            model_name='platformtask',
            new_name='finances_pl_source__316e03_idx',
            old_name='fin_platf_source__60fca2_idx',
        ),
        migrations.RenameIndex(
            model_name='platformtask',
            new_name='finances_pl_origin__510b83_idx',
            old_name='fin_platf_origin__f69369_idx',
        ),
        migrations.RenameIndex(
            model_name='platformtask',
            new_name='finances_pl_assigne_e47488_idx',
            old_name='fin_platf_assigne_5dc19d_idx',
        ),
    ]