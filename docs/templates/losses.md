In bioinformatics we often deal with missing values. When doing a multi-task classification, one might come across a case where not all the reponse values are allways present. For this purpose, one should mask the missing values and hence ignore them in our loss-function.

Default `MASK_VALUE` = -1. Hence when training our model:

```python
model.fit(X, y)
```

data-points where `y == -1` do not contribute to parameter update.


<!-- TODO - what numeber to take for regression -9999999999 ?  -->

## Available loss functions

{{autogenerated}}
