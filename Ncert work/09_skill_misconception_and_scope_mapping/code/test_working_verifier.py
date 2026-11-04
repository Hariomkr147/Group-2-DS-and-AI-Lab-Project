import unittest
from error_rules import corroborated_errors


class WorkingChecks(unittest.TestCase):
    def test_percentage_grid_and_counterexamples(self):
        for p in (5, 10, 20, 25, 40, 50):
            for n in (20, 40, 50, 80, 100, 120):
                question = f'{p}% of {n}'
                self.assertEqual([r['misconception_id'] for r in corroborated_errors(question,str(p*n),f'{n} * {p} = {n*p}')],['22482'])
                self.assertFalse(corroborated_errors(question,str(p*n),'I guessed'))
                self.assertFalse(corroborated_errors(question,str(p*n),f'I did not use {n} * {p} = {n*p}'))
                if p != 10:
                    from fractions import Fraction
                    out=str(Fraction(n,p))
                    self.assertEqual([r['misconception_id'] for r in corroborated_errors(question,out,f'{n} / {p} = {out}')],['26916'])
        self.assertFalse(corroborated_errors('10% of 50','5','50 / 10 = 5'))

    def test_fraction_operations_and_unsafe_inputs(self):
        cases=[('1/2 + 1/3','2/5','1+1=2\n2+3=5','19849'),
               ('1/2 * 1/3','3/2','1/2 * 3 = 3/2','22666'),
               ('1/2 ÷ 1/3','1/6','1/2 * 1/3 = 1/6','23021')]
        for q,a,w,mid in cases:
            self.assertEqual([r['misconception_id'] for r in corroborated_errors(q,a,w)],[mid])
            for bad in ('', '__import__("os")', '1 / 0 = 0', '1/2 * 1/3 = 9', '1+1=2\n2+3=4'):
                self.assertFalse(corroborated_errors(q,a,bad))

    def test_ratio_needs_explicit_wrong_percent_unit_and_checked_division(self):
        q='Convert the ratio to a percentage: 3 : 4'
        self.assertEqual([r['misconception_id'] for r in corroborated_errors(q,'0.75%','3 / 4 = 0.75')],['14036'])
        for a,w in [('75%','3 / 4 = 0.75'),('0.75','3 / 4 = 0.75'),('0.75%','3 / 4 = 0.8'),('0.75%','I guessed')]:
            self.assertFalse(corroborated_errors(q,a,w))


if __name__=='__main__':unittest.main()
