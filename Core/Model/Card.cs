using System;

namespace Splendor.Core.Model
{
    public enum Color
    {
        //1. White
        //2. Red      
        //3. Black
        //4. Green
        //5. Blue
        White = 1,
        Red = 2,
        Black = 3,
        Green = 4,
        Blue = 5,

        Gold = 6
    }
    public class Card
    {
        private string id;
        private int score;
        private Dictionary<Color, int> cost;
        private Color color;

        public Color Color{get;set;}

        public Card(string id, int score, Dictionary<Color,int> cost, Color color) 
        {
            this.id= id;
            this.score = score;
            this.cost = cost;
            this.color = color;
        }

        public string String() 
        {
            return string.Format("<ID,{0}>-<Score,{1}>-<Cost,{2}>-<Color,{3}>",this.id,this.score,this.cost.ToString(),this.color);
        }
    }

    public class CardSet
    {
        private Dictionary<Color, List<Card>> card_set;

        public CardSet()
        {
            this.card_set = new Dictionary<Color, List<Card>>();
        }

        public void Add(Card card) 
        {
            if(!this.card_set.ContainsKey(card.Color))
            {
                var set = new List<Card>();
                this.card_set.Add(card.Color, set);
            }
            this.card_set[card.Color].Add(card);
        }
    }
}